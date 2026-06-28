from typing import Optional

from sqlalchemy import ForeignKey, Integer, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.extensions import db


class Deployment(db.Model):
    __tablename__ = "deployments"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    name: Mapped[str] = mapped_column(String, nullable=False)
    pid: Mapped[str] = mapped_column(
        String(32), unique=True, nullable=False, index=True
    )
    api_key: Mapped[str] = mapped_column(String(32), nullable=False, index=True)


class User(db.Model):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    username: Mapped[Optional[str]] = mapped_column(String(16))
    password: Mapped[Optional[str]] = mapped_column(String(64))

    api_keys: Mapped[list["UserAPI"]] = relationship(
        back_populates="user", cascade="all, delete-orphan"
    )


# another zatar comment: errrrrrdeeeeeeeeeeer


class UserAPI(db.Model):
    __tablename__ = "user_api_rel"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    user_id: Mapped[int] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), nullable=False
    )
    api_key: Mapped[str] = mapped_column(String(32), unique=True, nullable=False)

    user: Mapped["User"] = relationship(back_populates="api_keys")
