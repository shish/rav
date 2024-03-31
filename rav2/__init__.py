import os
import hashlib
import functools
import click
import typing as t

from flask import (
    Flask,
    render_template,
    session,
    Response,
    redirect,
    url_for,
    request,
    abort,
    send_from_directory,
    g,
)
from .models import db, User, Avatar


std_width = 512


def create_app(test_config=None):
    ###################################################################
    # Load config

    app = Flask(__name__, instance_path=os.path.abspath("./data"))
    if not os.path.exists("./data"):  # pragma: no cover
        os.makedirs("./data")
    if not os.path.exists("./data/secret.txt"): # pragma: no cover
        with open("./data/secret.txt", "wb") as fp:
            fp.write(os.urandom(32))
    with open("./data/secret.txt", "rb") as fp:
        secret_key = fp.read()
    app.config.from_mapping(
        SECRET_KEY=secret_key,
        SQLALCHEMY_DATABASE_URI="sqlite:///rav.sqlite",
    )
    if test_config is None:
        # load the instance config, if it exists, when not testing
        app.config.from_pyfile("config.py", silent=True)
    else:
        # load the test config if passed in
        app.config.from_mapping(test_config)

    ###################################################################
    # Load database

    db.init_app(app)

    @click.command("init-db")
    def init_db_command():  # pragma: no cover
        """Clear the existing data and create new tables."""
        with app.app_context():
            db.create_all()
        click.echo("Initialized the database.")

    app.cli.add_command(init_db_command)

    ###################################################################
    # Route utils

    @app.before_request
    def load_logged_in_user():
        user_id = session.get("user_id")
        if user_id is None:
            g.user = None
        else:
            g.user = db.get_or_404(User, user_id)

    def login_required(view):
        @functools.wraps(view)
        def wrapped_view(**kwargs):
            if g.user is None:
                return redirect(url_for("index"))
            return view(**kwargs)

        return wrapped_view

    ###################################################################
    # Public routes

    @app.route("/favicon.ico")
    def favicon() -> Response:
        return send_from_directory(
            os.path.join(app.root_path, "static"),
            "favicon.ico",
            mimetype="image/vnd.microsoft.icon",
        )

    @app.route("/")
    def index() -> str:
        avatars = db.session.execute(
            db.select(Avatar)
            .filter(Avatar.enabled == True)
            .filter(Avatar.width <= std_width)
            .filter(Avatar.height <= std_width)
            .order_by(db.func.random())
            .limit(12)
        ).scalars()
        return render_template(
            "index.html",
            title="Shish's Avatar Hosting",
            heading="Shish's Avatar Hosting",
            user=g.user,
            avatars=avatars,
        )

    @app.route("/manual")
    def manual() -> str:
        return render_template(
            "manual.html",
            title="Manual",
            heading="Manual",
        )

    @app.route("/<path>.<ext>")
    @app.route("/<path>/<name>.<ext>")
    def avatar(
        path: str, name: t.Optional[str] = None, ext: t.Optional[str] = None
    ) -> Response:
        if len(path) == 32:
            avatar = db.first_or_404(db.select(Avatar).filter(Avatar.hash == path))
            return Response(avatar.data, mimetype="image/" + avatar.mime.lower())
        else:
            user = db.one_or_404(db.select(User).filter(User.username == path))
            avatar = db.first_or_404(
                db.select(Avatar)
                .filter(Avatar.owner == user)
                .filter(Avatar.enabled == True)
                .order_by(db.func.random())
            )
            # FIXME:
            # if request.form['has_key("scale"):
            #    scale = [int(n) for n in form["scale"].value.split("x")]
            #    avatar.scale(scale)
            return Response(avatar.data, mimetype="image/" + avatar.mime.lower())

    @app.route("/gallery")
    def gallery() -> str:
        user_counts = db.session.execute(
            db.text(
                """
                    select name as username, count(*) as count
                    from users
                    join avatars on avatars.owner_id=users.id
                    group by username
                    order by count desc
                    limit 35
                """
            )
        )
        new_avatars = db.session.execute(
            db.select(Avatar)
            .filter(Avatar.enabled == True)
            .filter(Avatar.width <= std_width)
            .filter(Avatar.height <= std_width)
            .order_by(-Avatar.id)
            .limit(8)
        ).scalars()
        random_avatars = db.session.execute(
            db.select(Avatar)
            .filter(Avatar.enabled == True)
            .filter(Avatar.width <= std_width)
            .filter(Avatar.height <= std_width)
            .order_by(db.func.random())
            .limit(16)
        ).scalars()

        return render_template(
            "gallery_list.html",
            title="Gallery List",
            heading="Gallery List",
            user_counts=user_counts,
            new_avatars=new_avatars,
            random_avatars=random_avatars,
        )

    @app.route("/<user_name>.html")
    def user_gallery(user_name: str) -> str:
        user = db.one_or_404(db.select(User).filter(User.username == user_name))
        return render_template(
            "gallery.html",
            title=f"{user_name}'s Avatar Gallery",
            heading=f"{user_name}'s Avatar Gallery",
            user=user,
        )

    ###################################################################
    # Create user / login / logout

    @app.route("/create", methods=["POST"])
    def create():
        username = request.form["username"]
        if not username:
            return abort(403, "Username is required")
        if len(username) >= 32:
            return abort(403, "Username needs to be less than 32 characters")

        user = db.session.execute(
            db.select(User).filter(
                db.func.lower(User.username) == db.func.lower(username)
            )
        ).scalar()
        if user:
            return abort(403, "That username has already been taken, sorry D:")

        password1 = request.form["password1"]
        password2 = request.form["password2"]
        if not password1:
            return abort(403, "Password is required")
        if password1 != password2:
            return abort(403, "The password and confirmation password don't match D:")

        email = request.form.get("email", "")

        user = User(username, password1, email)
        db.session.add(user)
        db.session.commit()

        session["user_id"] = user.id
        app.logger.info("User created")
        return redirect(url_for("user"))

    @app.route("/login", methods=["POST"])
    def login():
        username = request.form["username"]
        password = hashlib.md5(request.form["password"].encode("utf8")).hexdigest()

        user = db.one_or_404(
            db.select(User)
            .filter(db.func.lower(User.username) == db.func.lower(username))
            .filter(User.password == password),
            description="No user was found with that username + password",
        )
        session["user_id"] = user.id
        app.logger.info(f"logged in from {request.remote_addr}")
        return redirect(url_for("user"))

    @app.route("/logout")
    def logout():
        app.logger.info("logged out")
        session.clear()
        return redirect(url_for("index"))

    ###################################################################
    # Functions for logged-in users

    @app.route("/user")
    @login_required
    def user():
        return render_template(
            "user.html",
            title=g.user.username + "'s Page",
            heading=g.user.username + "'s Page",
            user=g.user,
        )

    @app.route("/toggle")
    @login_required
    def toggle():
        avatar = db.one_or_404(
            db.select(Avatar)
            .filter(Avatar.id == int(request.args["avatar_id"]))
            .filter(Avatar.owner_id == g.user.id)
        )

        avatar.enabled = not avatar.enabled
        db.session.commit()
        app.logger.info(
            "Avatar " + request.args["avatar_id"] + " set to " + str(avatar.enabled)
        )
        if request.args.get("ajax") == "yes":
            # FIXME: web.header('Content-Type', 'text/plain')
            if avatar.enabled:
                return "yes"
            else:
                return "no"
        else:
            return redirect(url_for("user"))

    @app.route("/delete")
    @login_required
    def delete():
        avatar = db.one_or_404(
            db.select(Avatar)
            .filter(Avatar.id == int(request.args["avatar_id"]))
            .filter(Avatar.owner_id == g.user.id)
        )
        db.session.delete(avatar)
        db.session.commit()
        app.logger.info("Avatar " + request.args["avatar_id"] + " removed")
        return redirect(url_for("user"))

    @app.route("/settings", methods=["POST"])
    @login_required
    def settings():
        g.user.message = request.form["message"]
        g.user.email = request.form["email"]
        db.session.commit()
        return redirect(url_for("user"))

    @app.route("/upload", methods=["POST"])
    @login_required
    def upload():
        f = request.files["avatar_data"]
        name = f.filename
        data = f.read()

        app.logger.info("Avatar uploaded: " + name)

        # some filenames include slashes o_O
        name = name.split("/")[-1]
        if len(name) > 32:
            name = name[-32:]

        g.user.avatars.append(Avatar(name, data))
        db.session.commit()
        return redirect(url_for("user"))

    return app
