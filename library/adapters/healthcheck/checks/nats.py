from faststream.nats import NatsBroker

from library.adapters.healthcheck.interface import CheckResult


class NatsHealthCheck:
    name = "nats"

    def __init__(self, broker: NatsBroker) -> None:
        self._broker = broker

    async def check(self) -> CheckResult:
        connection = getattr(self._broker, "_connection", None)
        if connection is None:
            raise RuntimeError("NATS broker not started")
        if getattr(connection, "is_connected", True) is False:
            raise RuntimeError("NATS not connected")
        return CheckResult(name=self.name, healthy=True)
