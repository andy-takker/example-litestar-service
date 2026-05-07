from enum import StrEnum, unique


@unique
class Permission(StrEnum):
    MANAGE_BOOKS = "manage_books"
    READ_BOOKS = "read_books"
    MANAGE_USERS = "manage_users"
    READ_USERS = "read_users"
