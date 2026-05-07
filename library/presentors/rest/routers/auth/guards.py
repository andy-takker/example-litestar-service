from collections.abc import Callable, Iterable

from litestar.connection import ASGIConnection
from litestar.exceptions import PermissionDeniedException
from litestar.handlers.base import BaseRouteHandler

from library.domains.entities.auth_user import AuthUser
from library.domains.entities.permission import Permission


def permission_guard(
    permissions: Iterable[Permission],
) -> Callable[[ASGIConnection, BaseRouteHandler], None]:
    required = frozenset(permissions)

    def _guard(connection: ASGIConnection, _: BaseRouteHandler) -> None:
        user: AuthUser = connection.user
        if user.is_superuser:
            return
        missing = required - user.permissions
        if missing:
            raise PermissionDeniedException(
                detail=f"Missing permissions: {sorted(p.value for p in missing)}",
            )

    return _guard


def any_permission_guard(
    permissions: Iterable[Permission],
) -> Callable[[ASGIConnection, BaseRouteHandler], None]:
    candidates = frozenset(permissions)

    def _guard(connection: ASGIConnection, _: BaseRouteHandler) -> None:
        user: AuthUser = connection.user
        if user.is_superuser:
            return
        if user.permissions.isdisjoint(candidates):
            raise PermissionDeniedException(
                detail=(f"Need at least one of: {sorted(p.value for p in candidates)}"),
            )

    return _guard
