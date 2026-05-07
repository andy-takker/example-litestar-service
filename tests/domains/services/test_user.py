from collections.abc import Sequence
from datetime import UTC, datetime
from uuid import UUID, uuid4

import pytest

from library.application.exceptions import EntityNotFoundException
from library.domains.entities.user import (
    CreateUser,
    UpdateUser,
    User,
    UserId,
    UserPagination,
    UserPaginationParams,
)
from library.domains.services.user import UserService


def _make_user(user_id: UUID | None = None, *, username: str = "alice") -> User:
    return User(
        id=UserId(user_id or uuid4()),
        username=username,
        email=f"{username}@example.com",
        is_superuser=False,
        permissions=frozenset(),
        created_at=datetime(2024, 1, 1, tzinfo=UTC),
        updated_at=datetime(2024, 1, 1, tzinfo=UTC),
    )


class FakeUserStorage:
    def __init__(
        self,
        *,
        user: User | None = None,
        exists: bool = True,
        listed: Sequence[User] = (),
        total: int = 0,
    ) -> None:
        self._user = user
        self._exists = exists
        self._listed = listed
        self._total = total
        self.calls: dict[str, int] = {}

    def _bump(self, name: str) -> None:
        self.calls[name] = self.calls.get(name, 0) + 1

    async def fetch_user_by_id(self, *, user_id: UserId) -> User | None:
        self._bump("fetch_user_by_id")
        return self._user

    async def count_users(self, *, params: UserPaginationParams) -> int:
        self._bump("count_users")
        return self._total

    async def fetch_user_list(self, *, params: UserPaginationParams) -> Sequence[User]:
        self._bump("fetch_user_list")
        return self._listed

    async def create_user(self, *, user: CreateUser) -> User:
        self._bump("create_user")
        return _make_user(username=user.username)

    async def delete_user_by_id(self, *, user_id: UserId) -> None:
        self._bump("delete_user_by_id")

    async def update_user_by_id(self, *, update_user: UpdateUser) -> User:
        self._bump("update_user_by_id")
        return _make_user(user_id=update_user.id)

    async def exists_user_by_id(self, *, user_id: UserId) -> bool:
        self._bump("exists_user_by_id")
        return self._exists


async def test_fetch_user_by_id_returns_user_when_present():
    expected = _make_user()
    service = UserService(user_storage=FakeUserStorage(user=expected))

    actual = await service.fetch_user_by_id(user_id=expected.id)

    assert actual is expected


async def test_fetch_user_by_id_raises_when_missing():
    service = UserService(user_storage=FakeUserStorage(user=None))

    with pytest.raises(EntityNotFoundException):
        await service.fetch_user_by_id(user_id=UserId(uuid4()))


async def test_fetch_user_list_returns_pagination():
    items = [_make_user(), _make_user(username="bob")]
    service = UserService(
        user_storage=FakeUserStorage(listed=items, total=42),
    )

    pagination = await service.fetch_user_list(
        params=UserPaginationParams(limit=10, offset=0),
    )

    assert pagination == UserPagination(total=42, items=items)


async def test_create_user_delegates_to_storage():
    storage = FakeUserStorage()
    service = UserService(user_storage=storage)

    user = await service.create_user(
        user=CreateUser(username="alice", email="alice@example.com"),
    )

    assert (user.username, storage.calls) == ("alice", {"create_user": 1})


async def test_delete_user_by_id_deletes_when_user_exists():
    storage = FakeUserStorage(exists=True)
    service = UserService(user_storage=storage)

    await service.delete_user_by_id(user_id=UserId(uuid4()))

    assert storage.calls == {"exists_user_by_id": 1, "delete_user_by_id": 1}


async def test_delete_user_by_id_raises_when_missing():
    storage = FakeUserStorage(exists=False)
    service = UserService(user_storage=storage)

    with pytest.raises(EntityNotFoundException):
        await service.delete_user_by_id(user_id=UserId(uuid4()))

    assert storage.calls == {"exists_user_by_id": 1}


async def test_update_user_by_id_updates_when_user_exists():
    storage = FakeUserStorage(exists=True)
    service = UserService(user_storage=storage)
    user_id = UserId(uuid4())

    user = await service.update_user_by_id(
        update_user=UpdateUser(id=user_id, username="bob"),
    )

    assert (user.id, storage.calls) == (
        user_id,
        {"exists_user_by_id": 1, "update_user_by_id": 1},
    )


async def test_update_user_by_id_raises_when_missing():
    storage = FakeUserStorage(exists=False)
    service = UserService(user_storage=storage)

    with pytest.raises(EntityNotFoundException):
        await service.update_user_by_id(
            update_user=UpdateUser(id=UserId(uuid4()), username="bob"),
        )

    assert storage.calls == {"exists_user_by_id": 1}
