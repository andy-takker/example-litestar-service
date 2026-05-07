from datetime import datetime
from http import HTTPStatus

from dishka.integrations.litestar import FromDishka, inject
from litestar import Controller, Request, get, post
from litestar.connection import ASGIConnection
from litestar.exceptions import NotAuthorizedException
from litestar.security.jwt import JWTAuth, Token
from pydantic import BaseModel, EmailStr, Field

from library.application.config import AuthConfig
from library.domains.entities.auth_user import AuthUser
from library.domains.entities.permission import Permission
from library.domains.entities.user import LoginUser, RegisterUser, UserId
from library.domains.use_cases.commands.auth.login_user import LoginUserCommand
from library.domains.use_cases.commands.auth.register_user import RegisterUserCommand
from library.presentors.rest.routers.auth.guards import permission_guard


class RegisterRequestSchema(BaseModel):
    username: str = Field(min_length=3, max_length=255)
    email: EmailStr = Field(min_length=3, max_length=255)
    password: str = Field(min_length=8, max_length=255)


class RegisteredUserSchema(BaseModel):
    id: UserId
    username: str
    email: EmailStr
    created_at: datetime


class LoginRequestSchema(BaseModel):
    username: str
    password: str


class RefreshRequestSchema(BaseModel):
    refresh_token: str


class TokenPairSchema(BaseModel):
    access_token: str
    refresh_token: str


class WhoAmISchema(BaseModel):
    id: str
    is_superuser: bool
    permissions: list[Permission]


class AdminZoneSchema(BaseModel):
    status: str


async def _retrieve_user(token: Token, connection: ASGIConnection) -> AuthUser:
    extras = token.extras or {}
    if extras.get("token_type") != "access":
        raise NotAuthorizedException(detail="Access token required")
    raw_permissions = extras.get("permissions") or []
    return AuthUser(
        id=token.sub,
        is_superuser=bool(extras.get("is_superuser", False)),
        permissions=frozenset(Permission(p) for p in raw_permissions),
    )


def make_jwt_auth(secret: str) -> JWTAuth[AuthUser]:
    return JWTAuth[AuthUser](
        retrieve_user_handler=_retrieve_user,
        token_secret=secret,
        exclude=[
            "/api",
            "/health",
            "/metrics",
            "/docs",
            "/schema",
            "/auth/login",
            "/auth/register",
            "/auth/refresh",
        ],
    )


def _create_token_pair(
    jwt_auth: JWTAuth[AuthUser],
    auth_config: AuthConfig,
    *,
    auth_user: AuthUser,
) -> TokenPairSchema:
    base_extras = {
        "permissions": [p.value for p in auth_user.permissions],
        "is_superuser": auth_user.is_superuser,
    }
    access = jwt_auth.create_token(
        identifier=auth_user.id,
        token_extras={**base_extras, "token_type": "access"},
        token_expiration=auth_config.access_token_ttl,
    )
    refresh = jwt_auth.create_token(
        identifier=auth_user.id,
        token_extras={**base_extras, "token_type": "refresh"},
        token_expiration=auth_config.refresh_token_ttl,
    )
    return TokenPairSchema(access_token=access, refresh_token=refresh)


class AuthController(Controller):
    path = "/auth"
    tags = ["Auth"]

    @post("/register", status_code=HTTPStatus.CREATED)
    @inject
    async def register(
        self,
        data: RegisterRequestSchema,
        register_user: FromDishka[RegisterUserCommand],
    ) -> RegisteredUserSchema:
        user = await register_user.execute(
            input_dto=RegisterUser(
                username=data.username,
                email=data.email,
                password=data.password,
            ),
        )
        return RegisteredUserSchema(
            id=user.id,
            username=user.username,
            email=user.email,
            created_at=user.created_at,
        )

    @post("/login", status_code=HTTPStatus.OK)
    @inject
    async def login(
        self,
        data: LoginRequestSchema,
        request: Request,
        login_user: FromDishka[LoginUserCommand],
        auth_config: FromDishka[AuthConfig],
    ) -> TokenPairSchema:
        jwt_auth: JWTAuth[AuthUser] = request.app.state.jwt_auth
        auth_user = await login_user.execute(
            input_dto=LoginUser(username=data.username, password=data.password),
        )
        return _create_token_pair(jwt_auth, auth_config, auth_user=auth_user)

    @post("/refresh", status_code=HTTPStatus.OK)
    @inject
    async def refresh(
        self,
        data: RefreshRequestSchema,
        request: Request,
        auth_config: FromDishka[AuthConfig],
    ) -> TokenPairSchema:
        jwt_auth: JWTAuth[AuthUser] = request.app.state.jwt_auth
        try:
            token = Token.decode(
                encoded_token=data.refresh_token,
                secret=jwt_auth.token_secret,
                algorithm=jwt_auth.algorithm,
            )
        except Exception as e:
            raise NotAuthorizedException(detail="Invalid refresh token") from e

        extras = token.extras or {}
        if extras.get("token_type") != "refresh":
            raise NotAuthorizedException(detail="Token is not a refresh token")

        auth_user = AuthUser(
            id=token.sub,
            is_superuser=bool(extras.get("is_superuser", False)),
            permissions=frozenset(
                Permission(p) for p in (extras.get("permissions") or [])
            ),
        )
        return _create_token_pair(jwt_auth, auth_config, auth_user=auth_user)

    @get("/me", status_code=HTTPStatus.OK)
    async def me(self, request: Request) -> WhoAmISchema:
        user: AuthUser = request.user
        return WhoAmISchema(
            id=user.id,
            is_superuser=user.is_superuser,
            permissions=sorted(user.permissions),
        )

    @get(
        "/admin-zone",
        status_code=HTTPStatus.OK,
        guards=[permission_guard([Permission.MANAGE_BOOKS])],
    )
    async def admin_zone(self) -> AdminZoneSchema:
        return AdminZoneSchema(status="you are in")
