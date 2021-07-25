#!/usr/bin/env python

import web
web.config.debug = False

import cgi
import logging
import logging.handlers
import hashlib

from sqlalchemy.orm import scoped_session, sessionmaker
from sqlalchemy import func
from models import *
from PIL import Image
import StringIO

urls = (
    '/?', 'index',
    '/index', 'index',
    '/manual', 'manual',
    '/timeline/(.*).(png|jpg|jpeg|gif)', 'timeline',
    '/([0-9a-f]{32}).*', 'avatar_by_hash',
    '/data/../([0-9a-f]{32}).*', 'avatar_by_hash',
    '/(.*).html', 'user_gallery',
    '/(.*).(gif|jpg|png|jpeg)', 'avatar_by_username',
    '/gallery', 'gallery',
    '/login', 'login',
    '/logout', 'logout',
    '/delete', 'delete',
    '/settings', 'settings',
    '/toggle', 'toggle',
    '/user', 'user',
    '/create', 'create',
    '/upload', 'upload',
    '/(favicon.ico)', 'static',
    '/static/(script.js|style.css)', 'static',
)


tagline = "[Rav - The Random Avatar Host]"
host = "http://rav.shishnet.org"


def getdata(fn):
    fp = open(fn, "rb")
    data = fp.read()
    fp.close()
    return data


def load_sqla(handler):
    web.ctx.orm = scoped_session(sessionmaker(bind=engine))
    try:
        return handler()
    except web.HTTPError:
        web.ctx.orm.commit()
        raise
    except:
        web.ctx.orm.rollback()
        raise
    finally:
        web.ctx.orm.commit()
        # If the above alone doesn't work, uncomment
        # the following line:
        #web.ctx.orm.expunge_all()


render = web.template.render("./templates/")
app = web.application(urls, globals())
app.add_processor(load_sqla)

import os, urlparse
db_info = urlparse.urlparse(os.environ['DB_DSN'])
session = web.session.Session(
    app,
    web.session.DBStore(
        web.database(
            dbn=db_info.scheme.replace("postgresql", "postgres"),
            host=db_info.hostname,
            port=db_info.port,
            db=db_info.path.strip("/"),
            user=db_info.username,
            pw=db_info.password),
        'sessions'
    ),
    initializer={'username': None}
)


# {{{ utility functions
class RavError(Exception):
    def __init__(self, title, message):
        self.title = title
        self.message = message


def log_info(text):
    if session.username:
        logging.info("%s: %s" % (session.username, text))
    else:
        logging.info("<anon>: %s" % text)


def if_logged_in(func):
    def splitter(*args):
        if session.username and web.ctx.orm.query(User).filter(User.username==session.username).first():
            return func(*args)
        else:
            web.seeother(host + "/")
    return splitter


def handle_exceptions(func):
    def logger(*args):
        try:
            return func(*args)
        except RavError, e:
            return render.standard("Error", e.title, "", e.message)
        except Exception, e:
            logging.exception("Unhandled exception:")
            return render.error(e)
    return logger


def avatar_to_td_user(avatar):
    owner_name = cgi.escape(avatar.owner.username)

    return """
        <td>
            <a href="%s.html"><img src="%s" alt="%s" width="%s" height="%s"><br>%s</a>
        </td>
    """ % (
        owner_name, cgi.escape(avatar.link), cgi.escape(avatar.filename),
        avatar.width, avatar.height, owner_name
    )


def avatar_to_td(avatar):
    if avatar.enabled:
        enabled = "enabled"
    else:
        enabled = "disabled"
    return """
        <td class="%s">
            <img src="%s" alt="%s" width="%s" height="%s">
            <br>%s
        </td>
    """ % (
        enabled, avatar.link, cgi.escape(avatar.filename),
        avatar.width, avatar.height, cgi.escape(avatar.filename)
    )


def avatar_to_td2(avatar):
    owner_name = cgi.escape(avatar.owner.username)

    return """
        <td>
            <a href="%s.html"><img src="%s" alt="%s" width="%s" height="%s"><br>%s</a>
        </td>
    """ % (owner_name, avatar.link, cgi.escape(avatar.filename), avatar.width, avatar.height, owner_name)


def avatar_to_td_edit(avatar):
    if avatar.enabled:
        eclass = "enabled"
        enabled = "yes"
    else:
        eclass = "disabled"
        enabled = "no"

    return """
        <td id="av%i" class="%s">
            <img src="%s" alt="%s">
            <br>%s
            <br>%ix%i
            <br><a href="delete?avatar_id=%i">Delete</a>
            <br><a href="toggle?avatar_id=%i" onclick="callToggle(%i); return false;">Toggle use</a>
            <br>(Current: <span id="on%i">%s</span>)
        </td>
    """ % (
        avatar.id, eclass,
        avatar.datalink, cgi.escape(avatar.filename), cgi.escape(avatar.filename),
        avatar.width, avatar.height, avatar.id, avatar.id, avatar.id, avatar.id, enabled
    )


def avatar_table(avatars, size=3, func=avatar_to_td):
    n = 0
    table = "<tr>"
    for avatar in avatars:
        table += func(avatar)
        n = n + 1
        if n % size == 0:
            table += "</tr><tr>"
    table += "</tr>"
    return table
# }}}


class index:
    def GET(self):
        title = "Shish's Avatar Hosting"
        avatars = web.ctx.orm.query(Avatar).filter(Avatar.enabled==True).filter(Avatar.width==150).filter(Avatar.height==150).order_by(func.random()).limit(12)
        table = avatar_table(avatars, 4, avatar_to_td2)
        body = render.index(session.username, table)
        return render.standard(title, title, "", body)


class avatar_by_username:
    @handle_exceptions
    def GET(self, user, ext):
        user = web.ctx.orm.query(User).filter(User.username==user).first()
        avatar = web.ctx.orm.query(Avatar).filter(Avatar.owner==user).filter(Avatar.enabled==True).order_by(func.random()).first()
        if user and avatar:
            # FIXME:
            #if form.has_key("scale"):
            #    scale = [int(n) for n in form["scale"].value.split("x")]
            #    avatar.scale(scale)
            web.header('Content-Type', avatar.mime)
            return getdata(avatar.datalink)
        else:
            raise RavError("Error", "No matching avatars found")


class timeline:
    @handle_exceptions
    def GET(self, user, format):
        FB_SIZE = 160

        user = web.ctx.orm.query(User).filter(User.username==user).first()
        #avatars = web.ctx.orm.query(Avatar).filter(Avatar.owner==user).filter(Avatar.enabled==True).order_by(func.random()).limit(50)
        avatars = web.ctx.orm.query(Avatar).filter(Avatar.owner==user)
        avatars = avatars.order_by(func.random()).limit(50)

        header = Image.new(mode='RGB', size=(851, 315), color=(0, 0, 0, 0))
        overlay = Image.open("fb/header-over.png")
        underlay = Image.open("fb/header-under.png")
        border = Image.open("fb/avatar-border.png")

        header.paste(underlay, (0, 0))

        offset = FB_SIZE + 25

        start_y = (199 - 22) + offset - 25
        current_y = start_y
        current_x = 20

        current_x = current_x - offset
        for avatar_obj in avatars:
            avatar = Image.open("."+avatar_obj.datalink)
            avatar = avatar.resize((FB_SIZE, FB_SIZE), Image.BICUBIC)

            if current_y < 0:
                # start a new column
                current_x = current_x + offset
                current_y = start_y = start_y + 25
            current_y = current_y - offset

            header.paste(border, (current_x-5, current_y-5), border)
            header.paste(avatar, (current_x, current_y))

        header.paste(overlay, (0, 0), overlay)

        buf = StringIO.StringIO()
        header.save(buf, format="JPEG", quality=95)
        web.header('Content-Type', "image/jpeg")
        return buf.getvalue()



class avatar_by_hash:
    def GET(self, hash):
        return getdata("/data/"+hash[0:2]+"/"+hash)


class static:
    def GET(self, filename):
        return getdata("static/" + filename)


class gallery:
    @handle_exceptions
    def GET(self):
        gallery_list = ""
        result = web.ctx.orm.execute("""
            select name as username, count(*) as count
            from users
            join avatars on avatars.owner_id=users.id
            group by username
            order by count desc
            limit 35
        """)
        for username, count in result:
            gallery_list += "<tr><td><a href='%s.html'>%s</a></td><td>%i</td></tr>" % (cgi.escape(username), username, count)

        avatars = web.ctx.orm.query(Avatar).filter(Avatar.enabled==True).filter(Avatar.width<=150).filter(Avatar.height<=150).order_by(-Avatar.id).limit(8)
        new_table = avatar_table(avatars, 4, avatar_to_td_user)

        avatars = web.ctx.orm.query(Avatar).filter(Avatar.enabled==True).filter(Avatar.width<=150).filter(Avatar.height<=150).order_by(func.random()).limit(16)
        random_table = avatar_table(avatars, 4, avatar_to_td_user)

        body = render.gallery_list(gallery_list, new_table, random_table)

        title = "Gallery List "+tagline
        heading = "Gallery List"
        return render.standard(title, heading, "", body)


class user_gallery:
    def GET(self, user_name):
        user = web.ctx.orm.query(User).filter(User.username==user_name).first()
        if user:
            table = avatar_table(user.avatars, 5, avatar_to_td)
            body = render.gallery(user, table)

            name = cgi.escape(user_name.replace("_", " ").capitalize())
            title = "%s's Avatar Gallery %s" % (name, tagline)
            heading = "%s's Avatar Gallery" % (name, )
            return render.standard(title, heading, "", body)
        else:
            raise RavError("Error", "User not found")


class manual:
    @handle_exceptions
    def GET(self):
        return render.standard("Manual", "Manual", "", render.manual())


class login:
    @handle_exceptions
    def POST(self):
        form = web.input()
        username = str(form.username)
        password = str(form.password)

        user = web.ctx.orm.query(User).filter(User.username==username).first()
        if user and user.password == hashlib.md5(password).hexdigest():
            session.username = username
            web.setcookie("username", username)
            log_info("logged in from %s" % (web.ctx.ip))
            web.seeother(host+"/user")
        else:
            raise RavError("Error", "User not found")


class logout:
    @handle_exceptions
    def GET(self):
        log_info("logged out")
        session.kill()
        web.seeother(host+"/")


class toggle:
    @handle_exceptions
    @if_logged_in
    def GET(self):
        form = web.input(ajax=False)
        avatar = web.ctx.orm.query(Avatar).filter(Avatar.id==int(form.avatar_id)).first()
        user   = web.ctx.orm.query(User).filter(User.username==session.username).first()
        if not avatar:
            raise RavError("Error", "No avatar found with that ID")
        if avatar.owner_id == user.id:
            avatar.enabled = not avatar.enabled
            log_info("Avatar "+form.avatar_id+" set to "+str(avatar.enabled))
            if form.ajax == "yes":
                web.header('Content-Type', 'text/plain')
                if avatar.enabled:
                    return "yes"
                else:
                    return "no"
            else:
                web.seeother(host+"/user")


class delete:
    @handle_exceptions
    @if_logged_in
    def GET(self):
        form = web.input()
        avatar = web.ctx.orm.query(Avatar).filter(Avatar.id==int(form.avatar_id)).first()
        user   = web.ctx.orm.query(User).filter(User.username==session.username).first()
        if not avatar:
            raise RavError("Error", "No avatar found with that ID")
        if avatar.owner_id == user.id:
            web.ctx.orm.delete(avatar)
            log_info("Avatar "+form.avatar_id+" removed")
            web.seeother(host+"/user")


class settings:
    @handle_exceptions
    @if_logged_in
    def POST(self):
        form = web.input()
        user = web.ctx.orm.query(User).filter(User.username==session.username).first()
        user.message = form.message
        user.email = form.email
        web.seeother(host+"/user")


class user:
    @handle_exceptions
    @if_logged_in
    def GET(self):
        user = web.ctx.orm.query(User).filter(User.username==session.username).first()
        if user:
            table = avatar_table(user.avatars, 5, avatar_to_td_edit)

            title = user.username+"'s Page"
            body = render.user(user, table)
            return render.standard(title, title, "", body)
        else:
            logging.warning("User logged in, but not found: %s" % session.username)
            raise RavError("Error", "User not found")


class create:
    @handle_exceptions
    def POST(self):
        form = web.input()
        username = form.username
        password1 = form.password1
        password2 = form.password2
        if len(form.email) > 0:
            email = form.email
        else:
            email = None

        user = web.ctx.orm.query(User).filter(User.username==username).first()
        if user == None:
            if password1 == password2:
                user = User(username, password1, email)
                web.ctx.orm.add(user)
                web.ctx.orm.commit()

                session.username = username
                log_info("User created")
                web.seeother(host+"/user")
            else:
                raise RavError("Password Error", "The password and confirmation password don't match D:")
        else:
            raise RavError("Name Taken", "That username has already been taken, sorry D:")


class upload:
    @handle_exceptions
    @if_logged_in
    def POST(self):
        form = web.input(avatar_data={})
        name = form.avatar_data.filename
        data = form.avatar_data.value

        log_info("Avatar uploaded: "+name)

        # some filenames include slashes o_O
        name = name.split("/")[-1]
        if len(name) > 32:
            name = name[-32:]

        user = web.ctx.orm.query(User).filter(User.username==session.username).first()
        try:
            user.avatars.append(Avatar(name, data))
            web.seeother(host+"/user")
        except IOError, e:
            raise RavError("Error adding avatar to database", str(e))


if __name__ == "__main__":
    logging.basicConfig(
        level=logging.DEBUG,
        format='%(asctime)s %(levelname)-8s %(message)s',
        # filename="../logs/app.log",
    )

    app.run()
