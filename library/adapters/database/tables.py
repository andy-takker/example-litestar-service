from sqlalchemy import JSON, Boolean, Index, Integer, String, text
from sqlalchemy.orm import Mapped, mapped_column

from library.adapters.database.base import BaseTable, IdentifableMixin, TimestampedMixin


class BookTable(BaseTable, TimestampedMixin, IdentifableMixin):
    __tablename__ = "books"
    __table_args__ = (
        Index(
            None,
            "title",
            "year",
            "author",
            unique=True,
            postgresql_where="deleted_at IS NULL",
        ),
    )

    title: Mapped[str] = mapped_column(String(255), nullable=False)
    year: Mapped[int] = mapped_column(Integer, nullable=False)
    author: Mapped[str] = mapped_column(String(255), nullable=False)


class UserTable(BaseTable, TimestampedMixin, IdentifableMixin):
    __tablename__ = "users"

    username: Mapped[str] = mapped_column(String(255), nullable=False, unique=True)
    email: Mapped[str] = mapped_column(String(255), nullable=False, unique=True)
    password_hash: Mapped[str | None] = mapped_column(String(255), nullable=True)
    is_superuser: Mapped[bool] = mapped_column(
        Boolean, nullable=False, server_default=text("false"), default=False
    )
    permissions: Mapped[list[str]] = mapped_column(
        JSON, nullable=False, server_default=text("'[]'::json"), default=list
    )
