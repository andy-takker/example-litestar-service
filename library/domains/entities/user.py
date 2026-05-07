from collections.abc import Mapping, Sequence
from dataclasses import dataclass, field
from datetime import datetime
from typing import NewType
from uuid import UUID

from library.application.entities import UNSET
from library.domains.entities.permission import Permission

UserId = NewType("UserId", UUID)


@dataclass(frozen=True, kw_only=True, slots=True)
class User:
    id: UserId
    username: str
    email: str
    is_superuser: bool
    permissions: frozenset[Permission]
    created_at: datetime
    updated_at: datetime


@dataclass(frozen=True, kw_only=True, slots=True)
class UserCredentials:
    id: UserId
    username: str
    password_hash: str
    is_superuser: bool
    permissions: frozenset[Permission]


@dataclass(frozen=True, kw_only=True, slots=True)
class UserPaginationParams:
    limit: int
    offset: int


@dataclass(frozen=True, kw_only=True, slots=True)
class UserPagination:
    total: int
    items: Sequence[User]


@dataclass(frozen=True, kw_only=True, slots=True)
class CreateUser:
    username: str
    email: str
    password_hash: str | None = None
    is_superuser: bool = False
    permissions: frozenset[Permission] = field(default_factory=frozenset)


@dataclass(frozen=True, kw_only=True, slots=True)
class RegisterUser:
    username: str
    email: str
    password: str


@dataclass(frozen=True, kw_only=True, slots=True)
class LoginUser:
    username: str
    password: str


@dataclass(frozen=True, kw_only=True, slots=True)
class UpdateUser:
    id: UserId
    username: str = UNSET
    email: str = UNSET

    def to_dict(self) -> Mapping[str, int | str]:
        values: dict[str, int | str] = {}
        if self.username is not UNSET:
            values["username"] = self.username
        if self.email is not UNSET:
            values["email"] = self.email
        return values
