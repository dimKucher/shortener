import hmac
from typing import Optional

from fastapi import HTTPException, Depends, Header
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from backend.app.logging import logger

from backend.app.config import config


class TokenAuth:
    """
    Класс для аутентификации по токену
    """

    def __init__(self):
        self.token = config.API_TOKEN
        self.token_header = config.TOKEN_HEADER_NAME

    async def verify_token(
            self,
            authorization: Optional[str] = Header(
                None, alias="Authorization"),
            x_api_token: Optional[str] = Header(
                None, alias=config.TOKEN_HEADER_NAME)
    ) -> str:
        """
        Универсальная проверка токена
        (поддерживает Bearer и X-API-Token)

        Args:
            authorization: Токен в формате Bearer
            x_api_token: Токен в кастомном заголовке

        Returns:
            str: Валидный токен

        Raises:
            HTTPException: Если токен невалидный
        """
        token = None
        token_source = None

        if authorization:
            parts = authorization.split()
            if len(parts) == 2 and parts[0].lower() == "bearer":
                token = parts[1]
                token_source = "Bearer"

        if not token and x_api_token:
            token = x_api_token
            token_source = config.TOKEN_HEADER_NAME

        if not token:
            raise HTTPException(
                status_code=401,
                detail={
                    "error": "MISSING_TOKEN",
                    "message": "Токен не предоставлен",
                    "solution": "Добавьте заголовок Authorization: "
                                f"Bearer <token> или "
                                f"{config.TOKEN_HEADER_NAME}: <token>"
                }
            )

        if not hmac.compare_digest(token, self.token):
            raise HTTPException(
                status_code=401,
                detail={
                    "error": "INVALID_TOKEN",
                    "message": "Неверный токен",
                    "solution": "Проверьте правильность токена"
                }
            )

        logger.info(f"Token {token_source}")

        return token

    async def verify_bearer_token(
            self,
            credentials: HTTPAuthorizationCredentials = Depends(
                HTTPBearer(auto_error=False))
    ) -> str:
        """
        Проверка только Bearer токена

        Args:
            credentials: Учетные данные из заголовка Authorization
        """
        if not credentials:
            raise HTTPException(
                status_code=401,
                detail={
                    "error": "MISSING_BEARER_TOKEN",
                    "message": "Отсутствует Bearer токен",
                    "solution": "Добавьте заголовок Authorization: Bearer <token>"
                },
                headers={"WWW-Authenticate": "Bearer"}
            )

        if not hmac.compare_digest(credentials.credentials, self.token):
            raise HTTPException(
                status_code=401,
                detail={
                    "error": "INVALID_TOKEN",
                    "message": "Неверный токен"
                },
                headers={"WWW-Authenticate": "Bearer"}
            )

        return credentials.credentials


token_auth = TokenAuth()
