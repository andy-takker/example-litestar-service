from dataclasses import dataclass, field
from enum import StrEnum, unique
from os import environ

import sentry_sdk
from sentry_sdk.integrations.asyncio import AsyncioIntegration


@unique
class SentryEnv(StrEnum):
    DEV = "DEV"
    PROD = "PROD"


@dataclass(frozen=True, kw_only=True, slots=True)
class SentryConfig:
    dsn: str = field(default_factory=lambda: environ.get("APP_SENTRY_DSN", ""))
    use_sentry: bool = field(
        default_factory=lambda: environ.get("APP_SENTRY_USE", "False").lower() == "true"
    )
    env: SentryEnv = field(
        default_factory=lambda: SentryEnv(
            environ.get("APP_SENTRY_ENV", SentryEnv.DEV).upper()
        )
    )
    traces_sample_rate: float = field(
        default_factory=lambda: float(
            environ.get("APP_SENTRY_TRACES_SAMPLE_RATE", "0.0")
        )
    )
    profiles_sample_rate: float = field(
        default_factory=lambda: float(
            environ.get("APP_SENTRY_PROFILES_SAMPLE_RATE", "0.0")
        )
    )


def setup_sentry(config: SentryConfig, release: str | None = None) -> None:
    if not config.dsn:
        raise ValueError("APP_SENTRY_DSN is not set")
    sentry_sdk.init(
        dsn=config.dsn,
        integrations=[AsyncioIntegration()],
        environment=config.env,
        traces_sample_rate=config.traces_sample_rate,
        profiles_sample_rate=config.profiles_sample_rate,
        release=release,
    )
