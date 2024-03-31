import os
import hashlib
import io

from PIL import Image
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship


class Base(DeclarativeBase):
    pass


db = SQLAlchemy(model_class=Base)


class User(db.Model):  # type: ignore
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(primary_key=True)
    username: Mapped[str] = mapped_column("name", nullable=False, index=True)
    password: Mapped[str] = mapped_column("pass", db.String(32), nullable=False)
    email: Mapped[str] = mapped_column(default="")
    message: Mapped[str] = mapped_column(default="")

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
    def common_size(self) -> str:
        # FIXME: incorrect, this takes the first size...
        sizes = ["%dx%d" % (a.width, a.height) for a in self.avatars]
        return sizes[0] if sizes else "0x0"


class Avatar(db.Model):  # type: ignore
    __tablename__ = "avatars"

    id: Mapped[int] = mapped_column(primary_key=True)
    owner_id: Mapped[int] = mapped_column(
        db.ForeignKey("users.id"), nullable=False, index=True
    )
    hash: Mapped[str] = mapped_column(db.String(32), nullable=False)
    filename: Mapped[str] = mapped_column(nullable=False)
    width: Mapped[int] = mapped_column(nullable=False)
    height: Mapped[int] = mapped_column(nullable=False)
    filesize: Mapped[int] = mapped_column(nullable=False)
    mime: Mapped[str] = mapped_column(nullable=False)
    enabled: Mapped[bool] = mapped_column(nullable=False, default=True)

    owner = relationship(
        "User",
        backref=db.backref(
            "avatars", cascade="all,delete-orphan", order_by=db.desc("id")
        ),
    )

    def __init__(self, name: str, data: bytes):
        img = Image.open(io.BytesIO(data))

        self.filename = name
        self.hash = hashlib.md5(data).hexdigest()
        self.filesize = len(data)
        self.width, self.height = img.size
        self.mime = img.format or "png"
        # if self.width > 150 or self.height > 150:
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
    def data(self) -> bytes:  # pragma: no cover
        with open(self.dataname, "rb") as fp:
            return fp.read()

    @data.setter
    def data(self, data: bytes) -> None:  # pragma: no cover
        os.makedirs(os.path.dirname(self.dataname), exist_ok=True)
        with open(self.dataname, "wb") as fp:
            fp.write(data)
