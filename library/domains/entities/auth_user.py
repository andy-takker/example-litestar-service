from dataclasses import dataclass, field

from library.domains.entities.permission import Permission


@dataclass(frozen=True, slots=True, kw_only=True)
class AuthUser:
    id: str
    is_superuser: bool = False
    permissions: frozenset[Permission] = field(default_factory=frozenset)
