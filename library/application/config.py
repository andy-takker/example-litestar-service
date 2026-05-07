from dataclasses import dataclass, field
from datetime import timedelta
from os import environ


@dataclass(frozen=True, kw_only=True, slots=True)
class AppConfig:
    title: str = field(default_factory=lambda: environ.get("APP_TITLE", "Library"))
    description: str = field(
        default_factory=lambda: environ.get(
            "APP_DESCRIPTION", "Web application for library"
        )
    )
    version: str = field(default_factory=lambda: environ.get("APP_VERSION", "1.0.0"))
    debug: bool = field(
        default_factory=lambda: environ.get("APP_DEBUG", "False").lower() == "true"
    )


@dataclass(frozen=True, kw_only=True, slots=True)
class HttpConfig:
    host: str = field(default_factory=lambda: environ.get("APP_HTTP_HOST", "0.0.0.0"))
    port: int = field(default_factory=lambda: int(environ.get("APP_HTTP_PORT", 8080)))


@dataclass(frozen=True, kw_only=True, slots=True)
class SecretConfig:
    secret: str = field(default_factory=lambda: environ.get("APP_SECRET", "secret"))


@dataclass(frozen=True, kw_only=True, slots=True)
class AuthConfig:
    access_token_ttl_seconds: int = field(
        default_factory=lambda: int(
            environ.get("APP_AUTH_ACCESS_TOKEN_TTL_SECONDS", "900")
        )
    )
    refresh_token_ttl_seconds: int = field(
        default_factory=lambda: int(
            environ.get("APP_AUTH_REFRESH_TOKEN_TTL_SECONDS", "604800")
        )
    )

    @property
    def access_token_ttl(self) -> timedelta:
        return timedelta(seconds=self.access_token_ttl_seconds)

    @property
    def refresh_token_ttl(self) -> timedelta:
        return timedelta(seconds=self.refresh_token_ttl_seconds)
