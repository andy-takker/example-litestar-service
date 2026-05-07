from collections.abc import Callable

import pytest
from passlib.context import CryptContext
from polyfactory.factories.sqlalchemy_factory import SQLAlchemyFactory
from sqlalchemy.ext.asyncio import AsyncSession

from library.adapters.database.tables import UserTable
from tests.utils import IterUse


class UserTableFactory(SQLAlchemyFactory[UserTable]):
    email = IterUse[str](lambda count: f"email{count}@example.com")
    username = IterUse[str](lambda count: f"username{count}")

    @classmethod
    def deleted_at(cls) -> None:
        return None

    @classmethod
    def password_hash(cls) -> None:
        return None

    @classmethod
    def is_superuser(cls) -> bool:
        return False

    @classmethod
    def permissions(cls) -> list[str]:
        return []


@pytest.fixture
def create_db_user_factory(session: AsyncSession) -> Callable:
    async def _factory(**kwargs) -> UserTable:
        user = UserTableFactory.build(**kwargs)
        session.add(user)
        await session.commit()
        await session.refresh(user)
        return user

    return _factory


@pytest.fixture(scope="session")
def crypt_context() -> CryptContext:
    return CryptContext(schemes=["argon2"], deprecated="auto")


@pytest.fixture
def register_db_user(
    create_db_user_factory: Callable,
    crypt_context: CryptContext,
) -> Callable:
    async def _register(
        *,
        username: str,
        password: str,
        permissions: list[str] | None = None,
        is_superuser: bool = False,
        email: str | None = None,
    ) -> UserTable:
        return await create_db_user_factory(
            username=username,
            email=email or f"{username}@example.com",
            password_hash=crypt_context.hash(password),
            is_superuser=is_superuser,
            permissions=permissions or [],
        )

    return _register
