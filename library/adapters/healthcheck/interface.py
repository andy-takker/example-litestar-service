from dataclasses import dataclass
from typing import Protocol, runtime_checkable


@dataclass(frozen=True, slots=True)
class CheckResult:
    name: str
    healthy: bool
    detail: str = "ok"


@runtime_checkable
class HealthCheck(Protocol):
    name: str

    async def check(self) -> CheckResult: ...
