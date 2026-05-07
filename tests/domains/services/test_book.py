from collections.abc import Sequence
from datetime import UTC, datetime
from uuid import UUID, uuid4

import pytest

from library.application.exceptions import EntityNotFoundException
from library.domains.entities.book import (
    Book,
    BookId,
    BookPagination,
    BookPaginationParams,
    CreateBook,
    UpdateBook,
)
from library.domains.services.book import BookService


def _make_book(book_id: UUID | None = None, *, title: str = "T") -> Book:
    return Book(
        id=BookId(book_id or uuid4()),
        title=title,
        year=2024,
        author="A",
        created_at=datetime(2024, 1, 1, tzinfo=UTC),
        updated_at=datetime(2024, 1, 1, tzinfo=UTC),
    )


class FakeBookStorage:
    def __init__(
        self,
        *,
        book: Book | None = None,
        exists: bool = True,
        listed: Sequence[Book] = (),
        total: int = 0,
    ) -> None:
        self._book = book
        self._exists = exists
        self._listed = listed
        self._total = total
        self.calls: dict[str, int] = {}

    def _bump(self, name: str) -> None:
        self.calls[name] = self.calls.get(name, 0) + 1

    async def fetch_book_by_id(self, *, book_id: BookId) -> Book | None:
        self._bump("fetch_book_by_id")
        return self._book

    async def count_books(self, *, params: BookPaginationParams) -> int:
        self._bump("count_books")
        return self._total

    async def fetch_book_list(self, *, params: BookPaginationParams) -> Sequence[Book]:
        self._bump("fetch_book_list")
        return self._listed

    async def create_book(self, *, book: CreateBook) -> Book:
        self._bump("create_book")
        return _make_book(title=book.title)

    async def delete_book_by_id(self, *, book_id: BookId) -> None:
        self._bump("delete_book_by_id")

    async def update_book_by_id(self, *, update_book: UpdateBook) -> Book:
        self._bump("update_book_by_id")
        return _make_book(book_id=update_book.id)

    async def exists_book_by_id(self, *, book_id: BookId) -> bool:
        self._bump("exists_book_by_id")
        return self._exists

    async def save_bulk_books(self, *, books: Sequence[CreateBook]) -> None:
        self._bump("save_bulk_books")


async def test_fetch_book_by_id_returns_book_when_present():
    expected = _make_book()
    service = BookService(book_storage=FakeBookStorage(book=expected))

    actual = await service.fetch_book_by_id(book_id=expected.id)

    assert actual is expected


async def test_fetch_book_by_id_raises_when_missing():
    service = BookService(book_storage=FakeBookStorage(book=None))

    with pytest.raises(EntityNotFoundException):
        await service.fetch_book_by_id(book_id=BookId(uuid4()))


async def test_fetch_book_list_returns_pagination():
    items = [_make_book(), _make_book()]
    service = BookService(
        book_storage=FakeBookStorage(listed=items, total=42),
    )

    pagination = await service.fetch_book_list(
        params=BookPaginationParams(limit=10, offset=0),
    )

    assert pagination == BookPagination(total=42, items=items)


async def test_create_book_delegates_to_storage():
    storage = FakeBookStorage()
    service = BookService(book_storage=storage)

    book = await service.create_book(
        book=CreateBook(title="X", year=2024, author="A"),
    )

    assert (book.title, storage.calls) == ("X", {"create_book": 1})


async def test_delete_book_by_id_deletes_when_book_exists():
    storage = FakeBookStorage(exists=True)
    service = BookService(book_storage=storage)

    await service.delete_book_by_id(book_id=BookId(uuid4()))

    assert storage.calls == {"exists_book_by_id": 1, "delete_book_by_id": 1}


async def test_delete_book_by_id_raises_when_missing():
    storage = FakeBookStorage(exists=False)
    service = BookService(book_storage=storage)

    with pytest.raises(EntityNotFoundException):
        await service.delete_book_by_id(book_id=BookId(uuid4()))

    assert storage.calls == {"exists_book_by_id": 1}


async def test_update_book_by_id_updates_when_book_exists():
    storage = FakeBookStorage(exists=True)
    service = BookService(book_storage=storage)
    book_id = BookId(uuid4())

    book = await service.update_book_by_id(
        update_book=UpdateBook(id=book_id, title="Z"),
    )

    assert (book.id, storage.calls) == (
        book_id,
        {"exists_book_by_id": 1, "update_book_by_id": 1},
    )


async def test_update_book_by_id_raises_when_missing():
    storage = FakeBookStorage(exists=False)
    service = BookService(book_storage=storage)

    with pytest.raises(EntityNotFoundException):
        await service.update_book_by_id(
            update_book=UpdateBook(id=BookId(uuid4()), title="Z"),
        )

    assert storage.calls == {"exists_book_by_id": 1}


async def test_save_bulk_books_delegates_to_storage():
    storage = FakeBookStorage()
    service = BookService(book_storage=storage)

    await service.save_bulk_books(
        books=[CreateBook(title="A", year=2024, author="X")],
    )

    assert storage.calls == {"save_bulk_books": 1}
