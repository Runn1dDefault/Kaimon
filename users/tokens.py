import json
from typing import Self, Any

import jwt
from django.conf import settings as server_settings
from django.core.cache import caches
from django.utils.crypto import get_random_string
from django.utils.functional import cached_property
from django.utils.translation import gettext_lazy
from rest_framework.exceptions import ValidationError
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

    def __init__(self, sub: Any):
        self.sub = sub

    @cached_property
    def live_seconds(self):
        return 60

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
    @cached_property
    def live_seconds(self):
        return settings["CODE_LIVE_SECONDS"]

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

    def _generate(self, payload: dict[str, Any], live_seconds: int = None) -> str:
        code = get_random_string(
            length=settings["TOKEN_LEN"],
            allowed_chars=settings["CODE_ALLOWED_CHARS"]
        )
        payload['code'] = code
        self._cache.set(self.cache_key, json.dumps(payload), timeout=live_seconds)
        return code

    def remove(self) -> None:
        self._cache.delete(self.cache_key)

    @classmethod
    def for_user(
        cls,
        user_id: int,
        live_seconds: int = None,
        raise_on_exist: bool = True,
    ) -> Self:
        restore_code = cls(sub=user_id)
        if raise_on_exist is True and restore_code.exist:
            raise RestoreCodeExist("code exist! Exp: %s seconds" % restore_code.exp)

        payload = {'user_id': user_id}
        restore_code._generate(payload, live_seconds=live_seconds or restore_code.live_seconds)
        return restore_code


class RestoreToken(BaseRestore):
    @cached_property
    def live_seconds(self):
        return settings["TOKEN_LIVE_SECONDS"]

    @cached_property
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
            algorithm="HS256"
        )
        self._cache.set(self.cache_key, token, timeout=self.live_seconds)
        return token

    @classmethod
    def _decode(cls, raw_token):
        return jwt.decode(raw_token, server_settings.SECRET_KEY, algorithms=["HS256"])

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


def generate_restore_token(user_id, code):
    """
    method of obtaining and validating code for a specific user
    if the code is in the cache for the send user_id,
    then it will be considered valid and a token will be generated
    the token will be saved in cache for a certain period set in settings.RESTORE_SETTINGS['TOKEN_LIVE_SECONDS']
    """
    try:
        token = RestoreToken.for_user(user_id=user_id, code=code)
    except InvalidRestoreCode as e:
        raise ValidationError({'detail': gettext_lazy(str(e))})
    else:
        RestoreCode(sub=user_id).remove()
        return token


def generate_confirm_code(user_id, raise_on_exist, live_seconds: int = None):
    """
    generates a new code for user_id and saves it in the cache for a certain period
    that is set in settings.RESTORE_SETTINGS['CODE_LIVE_SECONDS']
    raise_on_exist: if is True an error will be thrown if the code is already cached
    """
    try:
        code = RestoreCode.for_user(
            user_id=user_id,
            raise_on_exist=raise_on_exist,
            live_seconds=live_seconds
        )
    except RestoreCodeExist as e:
        raise ValidationError({'code': gettext_lazy(str(e))})
    else:
        return code
