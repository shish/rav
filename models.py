
import hashlib
from PIL import Image
import StringIO

from sqlalchemy import create_engine
from sqlalchemy import Column, Integer, String, Unicode, Boolean
from sqlalchemy import ForeignKey, desc
from sqlalchemy.orm import relationship, backref

import ConfigParser
config = ConfigParser.SafeConfigParser()
config.read("../app/rav.cfg")
host = config.get("database", "hostname")
user = config.get("database", "username")
password = config.get("database", "password")
database = config.get("database", "database")
engine = create_engine("postgres://%s:%s@%s/%s" % (user, password, host, database), echo=False)


from sqlalchemy.ext.declarative import declarative_base

Base = declarative_base()


class User(Base):
    __tablename__ = 'users'

    id       = Column(Integer, primary_key=True)
    username = Column('name', Unicode,    nullable=False, index=True)
    password = Column('pass', String(32), nullable=False)
    email    = Column(Unicode, default=u"")
    message  = Column(Unicode, default=u"")

    def __init__(self, username, password, email):
        self.username = username
        self.password = hashlib.md5(password).hexdigest()
        self.email = email

    def __repr__(self):
        return "<User('%s')>" % (self.name, )

    @property
    def num_avatars(self):
        return len(self.avatars)

    @property
    def num_active_avatars(self):
        return len([n for n in self.avatars if n.enabled])

    @property
    def common_size(self):
        # FIXME: incorrect, this takes the first size...
        return ["%dx%d" % (a.width, a.height) for a in self.avatars][0]


class Avatar(Base):
    __tablename__ = 'avatars'

    id       = Column(Integer,    primary_key=True)
    owner_id = Column(Integer,    ForeignKey('users.id'), nullable=False, index=True)
    hash     = Column(String(32), nullable=False)
    filename = Column(Unicode,    nullable=False)
    width    = Column(Integer,    nullable=False)
    height   = Column(Integer,    nullable=False)
    filesize = Column(Integer,    nullable=False)
    mime     = Column(String,     nullable=False)
    enabled  = Column(Boolean,    nullable=False, default=True)

    owner    = relationship(
                   "User",
                   backref=backref('avatars', cascade="all,delete-orphan", order_by=desc("id"))
               )

    def __init__(self, name, data):
        img = Image.open(StringIO.StringIO(data))

        self.filename = name
        self.hash     = hashlib.md5(data).hexdigest()
        self.filesize = len(data)
        self.width, self.height = img.size
        self.mime     = img.format

        #if self.width > 150 or self.height > 150:
        #    raise AvatarAddError("Avatar over-sized (max 150x150)")

        fd = open("data/%s/%s" % (self.hash[0:2], self.hash), "w")
        fd.write(data)
        fd.close()

    def __repr__(self):
        return "<Avatar('%s')>" % (self.filename, )

    @property
    def link(self):
        return "/%s/%s" % (self.hash, self.filename)

    @property
    def datalink(self):
        return "/data/" + self.hash[0:2] + "/" + self.hash


metadata = Base.metadata

if __name__ == "__main__":
    metadata.create_all(engine)
