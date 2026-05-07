from aiocache import BaseCache
from dishka import Provider, Scope, provide
from faststream.nats import NatsBroker
from sqlalchemy.ext.asyncio import AsyncEngine

from library.adapters.healthcheck.checks.nats import NatsHealthCheck
from library.adapters.healthcheck.checks.postgres import PostgresHealthCheck
from library.adapters.healthcheck.checks.redis import RedisHealthCheck
from library.adapters.healthcheck.runner import ReadinessRunner


class HealthCheckProvider(Provider):
    scope = Scope.APP

    @provide()
    def postgres_check(self, engine: AsyncEngine) -> PostgresHealthCheck:
        return PostgresHealthCheck(engine=engine)

    @provide()
    def redis_check(self, cache: BaseCache) -> RedisHealthCheck:
        return RedisHealthCheck(cache=cache)

    @provide()
    def nats_check(self, broker: NatsBroker) -> NatsHealthCheck:
        return NatsHealthCheck(broker=broker)

    @provide()
    def runner(
        self,
        postgres: PostgresHealthCheck,
        redis: RedisHealthCheck,
        nats: NatsHealthCheck,
    ) -> ReadinessRunner:
        return ReadinessRunner(checks=[postgres, redis, nats])
