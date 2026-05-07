from aiocache import BaseCache

from library.adapters.healthcheck.interface import CheckResult


class RedisHealthCheck:
    name = "redis"

    def __init__(self, cache: BaseCache) -> None:
        self._cache = cache

    async def check(self) -> CheckResult:
        await self._cache.exists("__health_ping__")
        return CheckResult(name=self.name, healthy=True)
