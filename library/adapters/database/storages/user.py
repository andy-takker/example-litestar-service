from collections.abc import Sequence
from datetime import UTC, datetime
from typing import NoReturn

from sqlalchemy import exists, func, insert, select, update
from sqlalchemy.exc import DBAPIError, IntegrityError, NoResultFound
from sqlalchemy.ext.asyncio import AsyncSession

from library.adapters.database.tables import UserTable
from library.adapters.database.uow import SqlalchemyUow
from library.application.exceptions import (
    EntityAlreadyExistsException,
    EntityNotFoundException,
    LibraryException,
)
from library.domains.entities.permission import Permission
from library.domains.entities.user import (
    CreateUser,
    UpdateUser,
    User,
    UserCredentials,
    UserId,
    UserPaginationParams,
)


class UserStorage:
    def __init__(self, *, uow: SqlalchemyUow) -> None:
        self._uow = uow

    @property
    def _session(self) -> AsyncSession:
        return self._uow.session

    async def fetch_user_by_id(self, *, user_id: UserId) -> User | None:
        stmt = select(UserTable).where(
            UserTable.id == user_id, UserTable.deleted_at.is_(None)
        )
        user = (await self._session.scalars(stmt)).first()
        if user is None:
            return None
        return _row_to_user(user)

    async def fetch_user_credentials_by_username(
        self, *, username: str
    ) -> UserCredentials | None:
        stmt = select(UserTable).where(
            UserTable.username == username, UserTable.deleted_at.is_(None)
        )
        user = (await self._session.scalars(stmt)).first()
        if user is None or user.password_hash is None:
            return None
        return UserCredentials(
            id=UserId(user.id),
            username=user.username,
            password_hash=user.password_hash,
            is_superuser=user.is_superuser,
            permissions=frozenset(Permission(p) for p in user.permissions),
        )

    async def exists_user_by_id(self, *, user_id: UserId) -> bool:
        stmt = select(
            exists().where(UserTable.id == user_id, UserTable.deleted_at.is_(None))
        )
        return bool((await self._session.execute(stmt)).scalar())

    async def count_users(self, *, params: UserPaginationParams) -> int:
        query = (
            select(func.count())
            .select_from(UserTable)
            .where(UserTable.deleted_at.is_(None))
        )
        result = (await self._session.execute(query)).scalar()
        return result or 0

    async def fetch_user_list(self, *, params: UserPaginationParams) -> Sequence[User]:
        query = (
            select(UserTable)
            .where(UserTable.deleted_at.is_(None))
            .limit(params.limit)
            .offset(params.offset)
        )
        rows = (await self._session.scalars(query)).all()
        return [_row_to_user(row) for row in rows]

    async def create_user(self, *, user: CreateUser) -> User:
        stmt = (
            insert(UserTable)
            .values(
                email=user.email,
                username=user.username,
                password_hash=user.password_hash,
                is_superuser=user.is_superuser,
                permissions=[p.value for p in user.permissions],
            )
            .returning(UserTable)
        )
        try:
            row = (await self._session.scalars(stmt)).one()
        except IntegrityError as e:
            self._raise_error(e)
        return _row_to_user(row)

    async def delete_user_by_id(self, *, user_id: UserId) -> None:
        stmt = (
            update(UserTable)
            .where(UserTable.id == user_id)
            .values(deleted_at=datetime.now(tz=UTC))
        )
        await self._session.execute(stmt)

    async def update_user_by_id(self, *, update_user: UpdateUser) -> User:
        stmt = (
            update(UserTable)
            .where(UserTable.id == update_user.id)
            .values(**update_user.to_dict())
            .returning(UserTable)
        )
        try:
            row = (await self._session.scalars(stmt)).one()
        except NoResultFound as e:
            raise EntityNotFoundException(entity=User, entity_id=update_user.id) from e
        return _row_to_user(row)

    def _raise_error(self, e: DBAPIError) -> NoReturn:
        constraint = e.__cause__.__cause__.constraint_name  # type: ignore[union-attr]

        if constraint in ("uq__users__username", "uq__users__email"):
            raise EntityAlreadyExistsException(message="User already exists") from e

        raise LibraryException(message="Unknown error") from e


def _row_to_user(row: UserTable) -> User:
    return User(
        id=UserId(row.id),
        email=row.email,
        username=row.username,
        is_superuser=row.is_superuser,
        permissions=frozenset(Permission(p) for p in row.permissions),
        created_at=row.created_at,
        updated_at=row.updated_at,
    )
