import json
from typing import Self, Any

import jwt
from django.conf import settings as server_settings
from django.core.cache import caches
from django.utils.crypto import get_random_string
from rest_framework_simplejwt.tokens import RefreshToken

from users.exceptions import InvalidRestoreCode, RestoreCodeExist

settings = server_settings.RESTORE_SETTINGS


def get_tokens_for_user(user):
    refresh = RefreshToken.for_user(user)
    return {
        'refresh': str(refresh),
        'access': str(refresh.access_token),
    }


class BaseRestore:
    _cache = caches[settings['CACHE_NAME']]
    LIVE: int = 60

    def __init__(self, sub: Any):
        self.sub = sub

    @property
    def cache_key(self) -> str:
        return str(self.sub)

    @property
    def exp(self) -> int | None:
        return self._cache.ttl(self.cache_key)

    @property
    def exist(self) -> bool:
        return bool(self._token)

    @property
    def _token(self):
        return self._cache.get(self.cache_key)

    def __str__(self):
        return self._token or ""

    def _generate(self, payload: dict[str, Any]):
        pass

    def verify(self, value) -> bool:
        return False

    @classmethod
    def for_user(cls, *args, **kwargs) -> Self:
        return cls(*args, **kwargs)

    def remove(self) -> None:
        return None


class RestoreCode(BaseRestore):
    LIVE = settings["CODE_LIVE_SECONDS"]

    @property
    def cache_key(self) -> str:
        return '%s%s' % (settings["CODE_PREFIX"], self.sub)

    @property
    def cached_payload(self):
        data = self._cache.get(self.cache_key)
        if data:
            return json.loads(data)

    @property
    def _token(self):
        if self.cached_payload:
            return self.cached_payload['code']

    def verify(self, code: str) -> bool:
        if self._token and self._token == code:
            return True
        return False

    def _generate(self, payload: dict[str, Any]) -> str:
        code = get_random_string(
            length=settings["TOKEN_LEN"],
            allowed_chars=settings["CODE_ALLOWED_CHARS"]
        )
        payload['code'] = code
        self._cache.set(self.cache_key, json.dumps(payload), timeout=self.LIVE)
        return code

    def remove(self) -> None:
        self._cache.delete(self.cache_key)

    @classmethod
    def for_user(cls, user_id: int, raise_on_exist: bool = True) -> Self:
        restore_code = cls(sub=user_id)
        if raise_on_exist and restore_code.exist:
            raise RestoreCodeExist("code exist! Exp: %s seconds" % restore_code.exp)
        payload = {'user_id': user_id}
        restore_code._generate(payload)
        return restore_code


class RestoreToken(BaseRestore):
    LIVE = settings["TOKEN_LIVE_SECONDS"]
    ALGORITHM = settings["TOKEN_ALGORITHM"]

    @property
    def cache_key(self) -> str:
        return '%s%s' % (settings["TOKEN_PREFIX"], self.sub)

    def verify(self, token: str | bytes) -> bool:
        if not self.exist:
            return False

        if isinstance(token, bytes):
            token = token.decode()

        if str(self._token) == str(token):
            return True
        return False

    def _generate(self, payload: dict[str, Any]) -> str:
        token = jwt.encode(
            payload,
            server_settings.SECRET_KEY,
            algorithm=self.ALGORITHM
        )
        self._cache.set(self.cache_key, token, timeout=self.LIVE)
        return token

    @classmethod
    def _decode(cls, raw_token):
        return jwt.decode(raw_token, server_settings.SECRET_KEY, algorithms=[cls.ALGORITHM])

    @classmethod
    def for_user(cls, user_id: int, code: str) -> Self:
        restore_code = RestoreCode(sub=user_id)
        if not restore_code.verify(code):
            raise InvalidRestoreCode("code %s invalid or expired!" % code)
        token = cls(sub=user_id)
        token._generate(payload={"user_id": user_id})
        return token

    @classmethod
    def for_token(cls, raw_token):
        payload = cls._decode(raw_token)
        return cls(sub=payload['user_id'])
