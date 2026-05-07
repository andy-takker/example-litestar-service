import asyncio
import logging
from collections.abc import Sequence

from library.adapters.healthcheck.interface import CheckResult, HealthCheck

log = logging.getLogger(__name__)


class ReadinessRunner:
    def __init__(
        self, checks: Sequence[HealthCheck], timeout_seconds: float = 2.0
    ) -> None:
        self._checks = checks
        self._timeout = timeout_seconds

    async def run(self) -> list[CheckResult]:
        return list(await asyncio.gather(*(self._safe_check(c) for c in self._checks)))

    async def _safe_check(self, check: HealthCheck) -> CheckResult:
        try:
            async with asyncio.timeout(self._timeout):
                return await check.check()
        except Exception as e:  # noqa: BLE001
            log.warning("Healthcheck %s failed: %s", check.name, e)
            return CheckResult(
                name=check.name,
                healthy=False,
                detail=f"error: {type(e).__name__}",
            )
