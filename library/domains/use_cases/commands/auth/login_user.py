from passlib.context import CryptContext
from passlib.exc import UnknownHashError

from library.application.exceptions import InvalidCredentialsException
from library.application.use_case import ICommand
from library.domains.entities.auth_user import AuthUser
from library.domains.entities.user import LoginUser
from library.domains.interfaces.storages.user import IUserStorage
from library.domains.uow import AbstractUow


class LoginUserCommand(ICommand[LoginUser, AuthUser]):
    def __init__(
        self,
        *,
        uow: AbstractUow,
        user_storage: IUserStorage,
        crypt_context: CryptContext,
    ) -> None:
        self._uow = uow
        self._user_storage = user_storage
        self._crypt_context = crypt_context

    async def execute(self, *, input_dto: LoginUser) -> AuthUser:
        async with self._uow:
            credentials = await self._user_storage.fetch_user_credentials_by_username(
                username=input_dto.username,
            )

        if credentials is None:
            raise InvalidCredentialsException(
                message="Invalid username or password",
            )
        try:
            valid = self._crypt_context.verify(
                input_dto.password, credentials.password_hash
            )
        except UnknownHashError as e:
            raise InvalidCredentialsException(
                message="Invalid username or password",
            ) from e
        if not valid:
            raise InvalidCredentialsException(
                message="Invalid username or password",
            )
        return AuthUser(
            id=str(credentials.id),
            is_superuser=credentials.is_superuser,
            permissions=credentials.permissions,
        )
