from uuid import UUID

from dirty_equals import IsUUID
from httpx import AsyncClient


async def test_response_includes_generated_request_id(client: AsyncClient) -> None:
    response = await client.get("/health/live")

    request_id = response.headers.get("x-request-id")
    assert UUID(hex=request_id) == IsUUID()


async def test_inbound_request_id_is_preserved(client: AsyncClient) -> None:
    given = "trace-abc-123"

    response = await client.get(
        "/health/live",
        headers={"X-Request-ID": given},
    )

    assert response.headers.get("x-request-id") == given


async def test_two_requests_get_distinct_generated_ids(client: AsyncClient) -> None:
    r1 = await client.get("/health/live")
    r2 = await client.get("/health/live")

    assert r1.headers["x-request-id"] != r2.headers["x-request-id"]
