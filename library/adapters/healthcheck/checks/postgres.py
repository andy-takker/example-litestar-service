from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncEngine

from library.adapters.healthcheck.interface import CheckResult


class PostgresHealthCheck:
    name = "postgres"

    def __init__(self, engine: AsyncEngine) -> None:
        self._engine = engine

    async def check(self) -> CheckResult:
        async with self._engine.connect() as conn:
            await conn.execute(text("SELECT 1"))
        return CheckResult(name=self.name, healthy=True)
