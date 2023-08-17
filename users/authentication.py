from django.contrib.auth import get_user_model
from django.core.exceptions import ObjectDoesNotExist
from django.utils.translation import gettext_lazy
from rest_framework_simplejwt.authentication import JWTAuthentication
from rest_framework_simplejwt.exceptions import InvalidToken, TokenError

from .tokens import RestoreToken


class RestoreJWTAuthentication(JWTAuthentication):
    def get_validated_token(self, raw_token):
        user_token = RestoreToken.for_token(raw_token)
        if not user_token.verify(raw_token):
            raise InvalidToken(gettext_lazy("Token invalid or expired!"), code="invalid_token")
        return user_token

    def get_user(self, validated_token):
        user_id = validated_token.sub
        try:
            user = get_user_model().objects.get(id=user_id)
        except ObjectDoesNotExist:
            raise InvalidToken(gettext_lazy("Invalid Token"), code='invalid_token')
        return user
