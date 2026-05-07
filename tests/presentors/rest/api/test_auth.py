from collections.abc import Callable
from http import HTTPStatus

import pytest
from dirty_equals import IsDatetime, IsStr, IsUUID
from httpx import AsyncClient

REGISTER_URL = "/auth/register"
LOGIN_URL = "/auth/login"
REFRESH_URL = "/auth/refresh"
ME_URL = "/auth/me"
ADMIN_ZONE_URL = "/auth/admin-zone"

DEFAULT_PASSWORD = "password123"


async def test_register__ok__status(client: AsyncClient):
    response = await client.post(
        REGISTER_URL,
        json={
            "username": "alice",
            "email": "alice@example.com",
            "password": DEFAULT_PASSWORD,
        },
    )
    assert response.status_code == HTTPStatus.CREATED


async def test_register__ok__format(client: AsyncClient):
    response = await client.post(
        REGISTER_URL,
        json={
            "username": "alice",
            "email": "alice@example.com",
            "password": DEFAULT_PASSWORD,
        },
    )
    assert response.json() == {
        "id": IsUUID(),
        "username": "alice",
        "email": "alice@example.com",
        "created_at": IsDatetime(iso_string=True),
    }


@pytest.mark.parametrize(
    "json_data",
    [
        {
            "username": "alice",
            "email": "alice@example.com",
            "password": "short",
        },
        {
            "username": "al",
            "email": "alice@example.com",
            "password": DEFAULT_PASSWORD,
        },
        {
            "username": "alice",
            "email": "not-an-email",
            "password": DEFAULT_PASSWORD,
        },
        {
            "username": "alice",
            "password": DEFAULT_PASSWORD,
        },
    ],
)
async def test_register__incorrect_data(client: AsyncClient, json_data):
    response = await client.post(REGISTER_URL, json=json_data)
    assert response.status_code == HTTPStatus.UNPROCESSABLE_ENTITY


async def test_register__duplicate_username__conflict(client: AsyncClient):
    payload = {
        "username": "alice",
        "email": "alice@example.com",
        "password": DEFAULT_PASSWORD,
    }
    await client.post(REGISTER_URL, json=payload)
    response = await client.post(
        REGISTER_URL,
        json={**payload, "email": "other@example.com"},
    )
    assert response.status_code == HTTPStatus.CONFLICT


async def test_login__ok__status(client: AsyncClient, register_db_user: Callable):
    await register_db_user(username="alice", password=DEFAULT_PASSWORD)
    response = await client.post(
        LOGIN_URL,
        json={"username": "alice", "password": DEFAULT_PASSWORD},
    )
    assert response.status_code == HTTPStatus.OK


async def test_login__ok__format(client: AsyncClient, register_db_user: Callable):
    await register_db_user(username="alice", password=DEFAULT_PASSWORD)
    response = await client.post(
        LOGIN_URL,
        json={"username": "alice", "password": DEFAULT_PASSWORD},
    )
    assert response.json() == {
        "access_token": IsStr(),
        "refresh_token": IsStr(),
    }


async def test_login__wrong_password__unauthorized(
    client: AsyncClient, register_db_user: Callable
):
    await register_db_user(username="alice", password=DEFAULT_PASSWORD)
    response = await client.post(
        LOGIN_URL,
        json={"username": "alice", "password": "wrong"},
    )
    assert response.status_code == HTTPStatus.UNAUTHORIZED


async def test_login__unknown_username__unauthorized(client: AsyncClient):
    response = await client.post(
        LOGIN_URL,
        json={"username": "ghost", "password": DEFAULT_PASSWORD},
    )
    assert response.status_code == HTTPStatus.UNAUTHORIZED


async def test_me__without_token__unauthorized(client: AsyncClient):
    response = await client.get(ME_URL)
    assert response.status_code == HTTPStatus.UNAUTHORIZED


async def test_me__with_invalid_token__unauthorized(client: AsyncClient):
    response = await client.get(
        ME_URL,
        headers={"Authorization": "Bearer not-a-real-token"},
    )
    assert response.status_code == HTTPStatus.UNAUTHORIZED


async def test_me__with_refresh_token__unauthorized(
    client: AsyncClient, register_db_user: Callable
):
    await register_db_user(username="alice", password=DEFAULT_PASSWORD)
    login = await client.post(
        LOGIN_URL,
        json={"username": "alice", "password": DEFAULT_PASSWORD},
    )
    response = await client.get(
        ME_URL,
        headers={"Authorization": f"Bearer {login.json()['refresh_token']}"},
    )
    assert response.status_code == HTTPStatus.UNAUTHORIZED


async def test_me__with_valid_token__ok(
    client: AsyncClient, register_db_user: Callable
):
    user = await register_db_user(
        username="alice",
        password=DEFAULT_PASSWORD,
        permissions=["read_books"],
    )
    login = await client.post(
        LOGIN_URL,
        json={"username": "alice", "password": DEFAULT_PASSWORD},
    )

    response = await client.get(
        ME_URL,
        headers={"Authorization": f"Bearer {login.json()['access_token']}"},
    )

    assert response.status_code == HTTPStatus.OK
    assert response.json() == {
        "id": str(user.id),
        "is_superuser": False,
        "permissions": ["read_books"],
    }


async def test_refresh__valid_refresh__new_pair(
    client: AsyncClient, register_db_user: Callable
):
    await register_db_user(
        username="alice",
        password=DEFAULT_PASSWORD,
        permissions=["read_books"],
    )
    login = await client.post(
        LOGIN_URL,
        json={"username": "alice", "password": DEFAULT_PASSWORD},
    )

    response = await client.post(
        REFRESH_URL,
        json={"refresh_token": login.json()["refresh_token"]},
    )

    assert response.status_code == HTTPStatus.OK
    assert response.json() == {
        "access_token": IsStr(),
        "refresh_token": IsStr(),
    }


async def test_refresh__access_token_passed_as_refresh__unauthorized(
    client: AsyncClient, register_db_user: Callable
):
    await register_db_user(username="alice", password=DEFAULT_PASSWORD)
    login = await client.post(
        LOGIN_URL,
        json={"username": "alice", "password": DEFAULT_PASSWORD},
    )

    response = await client.post(
        REFRESH_URL,
        json={"refresh_token": login.json()["access_token"]},
    )

    assert response.status_code == HTTPStatus.UNAUTHORIZED


async def test_refresh__invalid_token__unauthorized(client: AsyncClient):
    response = await client.post(
        REFRESH_URL,
        json={"refresh_token": "garbage-not-a-jwt"},
    )
    assert response.status_code == HTTPStatus.UNAUTHORIZED


async def test_admin_zone__without_required_permission__forbidden(
    client: AsyncClient, register_db_user: Callable
):
    await register_db_user(
        username="alice",
        password=DEFAULT_PASSWORD,
        permissions=["read_books"],
    )
    login = await client.post(
        LOGIN_URL,
        json={"username": "alice", "password": DEFAULT_PASSWORD},
    )

    response = await client.get(
        ADMIN_ZONE_URL,
        headers={"Authorization": f"Bearer {login.json()['access_token']}"},
    )

    assert response.status_code == HTTPStatus.FORBIDDEN


async def test_admin_zone__with_required_permission__ok(
    client: AsyncClient, register_db_user: Callable
):
    await register_db_user(
        username="alice",
        password=DEFAULT_PASSWORD,
        permissions=["manage_books"],
    )
    login = await client.post(
        LOGIN_URL,
        json={"username": "alice", "password": DEFAULT_PASSWORD},
    )

    response = await client.get(
        ADMIN_ZONE_URL,
        headers={"Authorization": f"Bearer {login.json()['access_token']}"},
    )

    assert response.status_code == HTTPStatus.OK
    assert response.json() == {"status": "you are in"}


async def test_admin_zone__superuser_bypasses_permissions__ok(
    client: AsyncClient, register_db_user: Callable
):
    await register_db_user(
        username="alice",
        password=DEFAULT_PASSWORD,
        is_superuser=True,
    )
    login = await client.post(
        LOGIN_URL,
        json={"username": "alice", "password": DEFAULT_PASSWORD},
    )

    response = await client.get(
        ADMIN_ZONE_URL,
        headers={"Authorization": f"Bearer {login.json()['access_token']}"},
    )

    assert response.status_code == HTTPStatus.OK
