from http import HTTPStatus

from dishka.integrations.litestar import FromDishka, inject
from litestar import Controller, Response, get

from library.adapters.healthcheck.runner import ReadinessRunner
from library.presentors.rest.routers.health.schemas import (
    CheckResultSchema,
    LivenessSchema,
    ReadinessSchema,
)


class HealthController(Controller):
    path = "/health"
    tags = ["Health"]
    include_in_schema = False

    @get("/live", status_code=HTTPStatus.OK)
    async def liveness(self) -> LivenessSchema:
        return LivenessSchema(status="ok")

    @get("/ready")
    @inject
    async def readiness(
        self,
        runner: FromDishka[ReadinessRunner],
    ) -> Response[ReadinessSchema]:
        results = await runner.run()
        all_ok = all(r.healthy for r in results)
        body = ReadinessSchema(
            status="ok" if all_ok else "fail",
            checks=[
                CheckResultSchema(name=r.name, healthy=r.healthy, detail=r.detail)
                for r in results
            ],
        )
        return Response(
            content=body,
            status_code=HTTPStatus.OK if all_ok else HTTPStatus.SERVICE_UNAVAILABLE,
        )
