from pydantic import BaseModel


class LivenessSchema(BaseModel):
    status: str


class CheckResultSchema(BaseModel):
    name: str
    healthy: bool
    detail: str


class ReadinessSchema(BaseModel):
    status: str
    checks: list[CheckResultSchema]
