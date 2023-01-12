import os
import hashlib
import io

from flask import Flask, render_template, session, Response, redirect, url_for, request, abort, send_from_directory
from flask_sqlalchemy import SQLAlchemy
from PIL import Image

tagline = "[Rav - The Random Avatar Host]"
host = "https://rav.shishnet.org"
std_width = 250

db = SQLAlchemy()
app = Flask(__name__, instance_path=os.path.abspath("./data"))
app.config["SQLALCHEMY_DATABASE_URI"] = "sqlite:///rav.sqlite"
db.init_app(app)
with open("./data/secret.txt", "rb") as fp:
    app.secret_key = fp.read()


#######################################################################
# Models

class User(db.Model):
    __tablename__ = 'users'

    id       = db.Column(db.Integer, primary_key=True)
    username = db.Column('name', db.Unicode,    nullable=False, index=True)
    password = db.Column('pass', db.String(32), nullable=False)
    email    = db.Column(db.Unicode, default=u"")
    message  = db.Column(db.Unicode, default=u"")

    def __init__(self, username: str, password: str, email: str) -> None:
        self.username = username
        self.password = hashlib.md5(password.encode("utf8")).hexdigest()
        self.email = email

    def __repr__(self) -> str:
        return f"User({self.username!r})"

    @property
    def num_avatars(self) -> int:
        return len(self.avatars)

    @property
    def num_active_avatars(self) -> int:
        return len([n for n in self.avatars if n.enabled])

    @property
    def common_size(self) -> int:
        # FIXME: incorrect, this takes the first size...
        sizes = ["%dx%d" % (a.width, a.height) for a in self.avatars]
        return sizes[0] if sizes else "0x0"


class Avatar(db.Model):
    __tablename__ = 'avatars'

    id       = db.Column(db.Integer,    primary_key=True)
    owner_id = db.Column(db.Integer,    db.ForeignKey('users.id'), nullable=False, index=True)
    hash     = db.Column(db.String(32), nullable=False)
    filename = db.Column(db.Unicode,    nullable=False)
    width    = db.Column(db.Integer,    nullable=False)
    height   = db.Column(db.Integer,    nullable=False)
    filesize = db.Column(db.Integer,    nullable=False)
    mime     = db.Column(db.String,     nullable=False)
    enabled  = db.Column(db.Boolean,    nullable=False, default=True)

    owner    = db.relationship(
        "User",
        backref=db.backref('avatars', cascade="all,delete-orphan", order_by=db.desc("id"))
    )

    def __init__(self, name: str, data: bytes):
        img = Image.open(io.BytesIO(data))

        self.filename = name
        self.hash     = hashlib.md5(data).hexdigest()
        self.filesize = len(data)
        self.width, self.height = img.size
        self.mime     = img.format
        #if self.width > 150 or self.height > 150:
        #    raise AvatarAddError("Avatar over-sized (max 150x150)")
        self.data = data

    def __repr__(self):
        return f"Avatar({self.filename!r})"

    @property
    def link(self):
        return f"/{self.hash}.{self.mime.lower()}"

    @property
    def dataname(self):
        return f"data/avatars/{self.hash[0:2]}/{self.hash}"

    @property
    def data(self) -> bytes:
        with open(self.dataname, "rb") as fp:
            return fp.read()

    @data.setter
    def data(self, data: bytes) -> None:
        os.makedirs(f"data/avatars/{self.hash[0:2]}", exist_ok=True)
        with open(f"data/avatars/{self.hash[0:2]}/{self.hash}", "wb") as fp:
            fp.write(data)

with app.app_context():
    db.create_all()


#######################################################################
# Exceptions

class RavError(Exception):
    def __init__(self, title, message):
        self.title = title
        self.message = message


#######################################################################
# Routes

@app.route('/favicon.ico')
def favicon():
    return send_from_directory(os.path.join(app.root_path, 'static'),
                               'favicon.ico', mimetype='image/vnd.microsoft.icon')

@app.route("/")
def index():
    avatars = db.session.execute(
        db.select(Avatar)
        .filter(Avatar.enabled==True)
        .filter(Avatar.width<=std_width)
        .filter(Avatar.height<=std_width)
        .order_by(db.func.random())
        .limit(12)
    ).scalars()
    return render_template(
        "index.jinja2",
        title="Shish's Avatar Hosting",
        heading="Shish's Avatar Hosting",
        username=session.get('username'),
        avatars=avatars,
    )

@app.route("/manual")
def manual():
    return render_template(
        "manual.jinja2",
        title="Manual",
        heading="Manual",
    )

@app.route("/<path>.<ext>")
def avatar(path: str, ext: str) -> bytes:
    if len(path) == 32:
        avatar = db.one_or_404(
            db.select(Avatar)
            .filter(Avatar.hash==path)
        )
        return Response(avatar.data, mimetype='image/'+avatar.mime.lower())
    else:
        user = db.one_or_404(
            db.select(User)
            .filter(User.username==path)
        )
        avatar = db.first_or_404(
            db.select(Avatar)
            .filter(Avatar.owner==user)
            .filter(Avatar.enabled==True)
            .order_by(db.func.random())
        )
        # FIXME:
        #if request.form['has_key("scale"):
        #    scale = [int(n) for n in form["scale"].value.split("x")]
        #    avatar.scale(scale)
        return Response(avatar.data, mimetype='image/'+avatar.mime.lower())

@app.route("/gallery")
def gallery():
    user_counts = db.session.execute(db.text("""
        select name as username, coalesce(count(*), 0) as count
        from users
        join avatars on avatars.owner_id=users.id
        group by username
        order by count desc
        limit 35
    """))
    new_avatars = db.session.execute(
        db.select(Avatar)
        .filter(Avatar.enabled==True)
        .filter(Avatar.width<=std_width)
        .filter(Avatar.height<=std_width)
        .order_by(-Avatar.id)
        .limit(8)
    ).scalars()
    random_avatars = db.session.execute(
        db.select(Avatar)
        .filter(Avatar.enabled==True)
        .filter(Avatar.width<=std_width)
        .filter(Avatar.height<=std_width)
        .order_by(db.func.random())
        .limit(16)
    ).scalars()

    return render_template(
        "gallery_list.jinja2",
        title="Gallery List "+tagline,
        heading="Gallery List",
        user_counts=user_counts,
        new_avatars=new_avatars,
        random_avatars=random_avatars,
    )

@app.route("/<user_name>.html")
def user_gallery(user_name):
    user = db.one_or_404(
        db.select(User)
        .filter(User.username==user_name)
    )
    return render_template(
        "gallery.jinja2",
        title="%s's Avatar Gallery %s" % (user_name, tagline),
        heading="%s's Avatar Gallery" % (user_name, ),
        user=user,
    )

@app.route("/login", methods=['POST'])
def login():
    username = request.form['username']
    password = hashlib.md5(request.form['password'].encode("utf8")).hexdigest()

    user = db.one_or_404(
        db.select(User)
        .filter(User.username==username)
        .filter(User.password==password)
    )
    session['username'] = username
    app.logger.info("logged in from %s" % (request.remote_addr))
    return redirect(url_for("index"))

@app.route("/logout")
def logout():
    app.logger.info("logged out")
    session.pop('username', None)
    return redirect(url_for('index'))

@app.route("/toggle")
def toggle():
    if "username" not in session:
        return abort(403)
    avatar = db.one_or_404(
        db.select(Avatar)
        .filter(Avatar.id==int(request.args['avatar_id']))
    )
    user = db.one_or_404(
        db.select(User)
        .filter(User.username==session['username'])
    )
    if avatar.owner_id == user.id:
        avatar.enabled = not avatar.enabled
        db.session.commit()
        app.logger.info("Avatar "+request.args['avatar_id']+" set to "+str(avatar.enabled))
        if request.args['ajax'] == "yes":
            # FIXME: web.header('Content-Type', 'text/plain')
            if avatar.enabled:
                return "yes"
            else:
                return "no"
        else:
            return redirect(url_for("user"))

@app.route("/delete")
def delete():
    if "username" not in session:
        return abort(403)
    avatar = db.one_or_404(
        db.select(Avatar)
        .filter(Avatar.id==int(request.args['avatar_id']))
    )
    user = db.one_or_404(
        db.select(User)
        .filter(User.username==session['username'])
    )
    if avatar.owner_id == user.id:
        db.session.delete(avatar)
        db.session.commit()
        app.logger.info("Avatar "+request.args['avatar_id']+" removed")
        return redirect(url_for("user"))

@app.route("/settings", methods=['POST'])
def settings():
    if "username" not in session:
        return abort(403)
    user = db.one_or_404(
        db.select(User)
        .filter(User.username==session['username'])
    )
    user.message = request.form['message']
    user.email = request.form['email']
    db.session.commit()
    return redirect(url_for("user"))

@app.route("/user")
def user():
    if "username" not in session:
        return abort(403)
    user = db.one_or_404(
        db.select(User)
        .filter(User.username==session['username'])
    )
    return render_template(
        "user.jinja2",
        title=user.username+"'s Page",
        heading=user.username+"'s Page",
        user=user,
    )

@app.route("/create", methods=['POST'])
def create():
    username = request.form['username']

    password1 = request.form['password1']
    password2 = request.form['password2']
    if password1 != password2:
        raise RavError("Password Error", "The password and confirmation password don't match D:")

    if len(request.form['email']) > 0:
        email = request.form['email']
    else:
        email = None

    user = db.session.execute(
        db.select(User)
        .filter(User.username==username)
    ).scalar()
    if user:
        raise RavError("Name Taken", "That username has already been taken, sorry D:")

    user = User(username, password1, email)
    db.session.add(user)
    db.session.commit()

    session['username'] = username
    app.logger.info("User created")
    return redirect(url_for("user"))

@app.route("/upload", methods=['POST'])
def upload():
    if "username" not in session:
        return abort(403)

    f = request.files['avatar_data']
    name = f.filename
    data = f.read()

    app.logger.info("Avatar uploaded: "+name)

    # some filenames include slashes o_O
    name = name.split("/")[-1]
    if len(name) > 32:
        name = name[-32:]

    user = db.one_or_404(
        db.select(User)
        .filter(User.username==session['username'])
    )
    try:
        user.avatars.append(Avatar(name, data))
        db.session.commit()
        return redirect(url_for("user"))
    except IOError as e:
        raise RavError("Error adding avatar to database", str(e))
