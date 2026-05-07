from http import HTTPStatus

import pytest
from httpx import AsyncClient

from library.adapters.healthcheck.interface import CheckResult
from library.adapters.healthcheck.runner import ReadinessRunner


async def test_liveness_always_ok(client: AsyncClient) -> None:
    response = await client.get("/health/live")
    assert response.status_code == HTTPStatus.OK
    assert response.json() == {"status": "ok"}


async def test_readiness_when_all_checks_pass(
    client: AsyncClient,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    async def all_ok(self: ReadinessRunner) -> list[CheckResult]:
        return [
            CheckResult(name="postgres", healthy=True),
            CheckResult(name="redis", healthy=True),
            CheckResult(name="nats", healthy=True),
        ]

    monkeypatch.setattr(ReadinessRunner, "run", all_ok)

    response = await client.get("/health/ready")

    assert response.status_code == HTTPStatus.OK
    assert response.json() == {
        "checks": [
            {"detail": "ok", "healthy": True, "name": "postgres"},
            {"detail": "ok", "healthy": True, "name": "redis"},
            {"detail": "ok", "healthy": True, "name": "nats"},
        ],
        "status": "ok",
    }


async def test_readiness_when_db_down(
    client: AsyncClient,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    async def db_down(self: ReadinessRunner) -> list[CheckResult]:
        return [
            CheckResult(
                name="postgres",
                healthy=False,
                detail="error: ConnectionRefusedError",
            ),
            CheckResult(name="redis", healthy=True),
            CheckResult(name="nats", healthy=True),
        ]

    monkeypatch.setattr(ReadinessRunner, "run", db_down)

    response = await client.get("/health/ready")

    assert response.status_code == HTTPStatus.SERVICE_UNAVAILABLE
    assert response.json() == {
        "checks": [
            {
                "detail": "error: ConnectionRefusedError",
                "healthy": False,
                "name": "postgres",
            },
            {"detail": "ok", "healthy": True, "name": "redis"},
            {"detail": "ok", "healthy": True, "name": "nats"},
        ],
        "status": "fail",
    }
