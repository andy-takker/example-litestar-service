from passlib.context import CryptContext

from library.application.exceptions import EntityAlreadyExistsException
from library.application.use_case import ICommand
from library.domains.entities.user import CreateUser, RegisterUser, User
from library.domains.interfaces.storages.user import IUserStorage
from library.domains.uow import AbstractUow


class RegisterUserCommand(ICommand[RegisterUser, User]):
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

    async def execute(self, *, input_dto: RegisterUser) -> User:
        password_hash = self._crypt_context.hash(input_dto.password)
        async with self._uow:
            try:
                return await self._user_storage.create_user(
                    user=CreateUser(
                        username=input_dto.username,
                        email=input_dto.email,
                        password_hash=password_hash,
                    )
                )
            except EntityAlreadyExistsException:
                raise
