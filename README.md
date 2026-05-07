# Example Litestar Service

A reference Python web service built on [Litestar](https://github.com/litestar-org/litestar) — a working template for production REST + async services with clean architecture, observability, JWT auth and RBAC.

The service implements a small "library" domain (books, users, OpenLibrary integration, async book upload via NATS) and is meant to be cloned and adapted under your project, not used as-is.

## Features

- **Layered architecture** (`domains` / `adapters` / `presentors` / `application`) with import boundaries enforced by [import-linter](https://github.com/seddonym/import-linter)
- **DI** via [dishka](https://github.com/reagento/dishka) (App + Request scopes, managed lifecycle for engine / Redis / HTTP / NATS broker)
- **Two transports in one app**: REST (Litestar) + async pub/sub ([FastStream](https://github.com/ag2ai/faststream) + NATS JetStream)
- **JWT auth**: `/auth/register`, `/auth/login`, `/auth/refresh`, `/auth/me` — access + refresh token pair, TTLs configurable via env
- **RBAC**: `Permission` enum, `AuthUser` entity, `permission_guard` / `any_permission_guard` for route-level protection
- **Password hashing** with [passlib + argon2](https://passlib.readthedocs.io/en/stable/lib/passlib.hash.argon2.html)
- **Health probes**: `/health/live` (liveness) and `/health/ready` (parallel Postgres / Redis / NATS checks with timeouts) backed by a dedicated adapter
- **Observability**: Prometheus on `/metrics`, structlog (console in dev, JSON in prod), Sentry with traces and profiles sampling
- **Request correlation**: middleware sets `X-Request-ID`, binds it to `structlog.contextvars` and echoes it back in the response
- **Database**: SQLAlchemy + asyncpg + alembic, UoW pattern around async sessions
- **Hybrid serialization**: Pydantic at the REST boundary, msgspec inside adapters (no hard coupling to Pydantic)
- **Testing diamond**: unit tests for domain services with `FakeStorage`, integration tests for DB / REST / NATS against real Postgres + Redis + NATS in docker-compose, ~94% coverage
- **Tooling**: ruff, mypy, import-linter, pytest + coverage, pre-commit, uv

## Quick start

```bash
make develop                                              # create .venv via uv, install deps, set up pre-commit
make local                                                # start Postgres + Redis + NATS via docker-compose (foreground)
# in another terminal:
set -a && source .env.dev && set +a                       # load default env
.venv/bin/python -m library.adapters.database upgrade head  # apply migrations
.venv/bin/python -m library                               # serve on http://127.0.0.1:8000
```

OpenAPI UIs:

- <http://127.0.0.1:8000/docs/swagger>
- <http://127.0.0.1:8000/docs/redoc>

## Working with the repo

### Install dependencies

Creates a fresh `.venv` via `uv sync` and installs pre-commit hooks:

```bash
make develop
```

### Run dev containers

Starts Postgres, Redis and NATS from `docker-compose.dev.yaml`:

```bash
make local
```

Stop and clean up volumes:

```bash
make local-down
```

### Run tests

DB containers must be up (`make local` running in another terminal):

```bash
.venv/bin/pytest -vx ./tests
```

For CI-style with coverage report:

```bash
make test-ci
```

The minimum coverage is set to 80% in `pyproject.toml`; current coverage is above 90%.

### Run linters

```bash
make lint-ci    # ruff + mypy + import-linter
```

Or individually:

```bash
.venv/bin/ruff check ./library
.venv/bin/mypy --config-file ./pyproject.toml ./library
.venv/bin/lint-imports
```

`import-linter` enforces these architectural contracts:

- `library` must not import `tests`
- `library.domains` must not import `library.adapters`
- `library.domains` must not import `library.presentors`
- `library.adapters` must not import `library.presentors`

### Database migrations

Apply all migrations to head:

```bash
.venv/bin/python -m library.adapters.database upgrade head
```

Generate a new migration after changing tables in [library/adapters/database/tables.py](library/adapters/database/tables.py):

```bash
.venv/bin/python -m library.adapters.database revision --autogenerate -m "your message"
```

Both commands require `APP_DATABASE_*` env vars to point at a running Postgres.

### CI workflow

```bash
make develop-ci  # install deps without venv (CI runs as root in container)
make lint-ci     # ruff + mypy + import-linter
make test-ci     # pytest with junit + coverage report
```

## Configuration

All configuration goes through environment variables, parsed by `dataclass`-based config objects in [library/application/config.py](library/application/config.py) and per-adapter `config.py` files. A working set of defaults for local development is in [.env.dev](.env.dev).

Key variables:

| Variable | Default | Notes |
| --- | --- | --- |
| `APP_DATABASE_HOST` / `_PORT` / `_USER` / `_PASSWORD` / `_NAME` | from `.env.dev` | Postgres connection |
| `APP_REDIS_HOST` / `APP_REDIS_PORT` | `127.0.0.1` / `6379` | |
| `APP_NATS_HOST` / `APP_NATS_PORT` | `127.0.0.1` / `4222` | |
| `APP_HTTP_HOST` / `APP_HTTP_PORT` | `0.0.0.0` / `8080` | |
| `APP_SECRET` | `secret` | JWT signing secret. **Must be set in prod.** |
| `APP_AUTH_ACCESS_TOKEN_TTL_SECONDS` | `900` | 15 minutes |
| `APP_AUTH_REFRESH_TOKEN_TTL_SECONDS` | `604800` | 7 days |
| `APP_LOG_LEVEL` | `DEBUG` | |
| `APP_LOG_JSON` | `true` | JSON logs in prod, set to `false` for console output |
| `APP_SENTRY_USE` | `False` | |
| `APP_SENTRY_DSN` | empty | |
| `APP_SENTRY_TRACES_SAMPLE_RATE` | `0.0` | |
| `APP_SENTRY_PROFILES_SAMPLE_RATE` | `0.0` | |

## Routes

OpenAPI is the source of truth — open <http://127.0.0.1:8000/docs/swagger> after starting the service. Reference list:

### Auth

```text
POST    /auth/register             Register a new user (username + email + password)
POST    /auth/login                Log in by username + password, returns access + refresh
POST    /auth/refresh              Refresh access + refresh token pair
GET     /auth/me                   Get current user from Bearer access token
GET     /auth/admin-zone           Demo of permission_guard ([Permission.MANAGE_BOOKS])
```

### Books

```text
GET     /api/v1/books/             Fetch books (paginated)
POST    /api/v1/books/             Create a book
GET     /api/v1/books/{book_id}/   Fetch book by ID
PATCH   /api/v1/books/{book_id}/   Update book by ID
DELETE  /api/v1/books/{book_id}/   Delete book by ID
```

### Users

```text
GET     /api/v1/users/             Fetch users (paginated)
POST    /api/v1/users/             Create user (admin CRUD; no password is set)
GET     /api/v1/users/{user_id}/   Fetch user by ID
PATCH   /api/v1/users/{user_id}/   Update user by ID
DELETE  /api/v1/users/{user_id}/   Delete user by ID
```

### OpenLibrary

```text
GET     /api/v1/open-library/search?query=...   Search books on OpenLibrary
```

### Service / observability

```text
GET     /metrics                   Prometheus metrics
GET     /health/live               Liveness probe (always 200 while process is alive)
GET     /health/ready              Readiness probe (Postgres + Redis + NATS, 200 or 503)
GET     /docs                      OpenAPI JSON
GET     /docs/swagger              Swagger UI
GET     /docs/redoc                Redoc UI
```

## Project layout

```text
library/
├── application/        Logging, exceptions, base config, Sentry setup
├── adapters/           Outbound: database, redis, nats, open_library, healthcheck
├── domains/            Entities, interfaces, services, use cases (no infra imports)
└── presentors/
    ├── rest/           Litestar app, controllers, middleware, route handlers
    └── faststream/     NATS subscribers
tests/
├── domains/services/   Unit tests of domain services with FakeStorage
├── adapters/           Integration tests against real Postgres / Redis / HTTP
└── presentors/         REST + FastStream integration tests
```

## License

MIT.
