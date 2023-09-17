from django.contrib.auth import get_user_model
from django.utils.translation import gettext_lazy
from rest_framework.exceptions import ValidationError

from users.exceptions import InvalidRestoreCode, RestoreCodeExist
from users.tokens import RestoreToken, RestoreCode


def create_restore_token(user_id, code):
    try:
        token = RestoreToken.for_user(user_id=user_id, code=code)
    except InvalidRestoreCode as e:
        raise ValidationError({'detail': gettext_lazy(str(e))})
    else:
        RestoreCode(sub=user_id).remove()
        return token


def create_confirm_code(user_id, raise_on_exist):
    try:
        code = RestoreCode.for_user(user_id=user_id, raise_on_exist=raise_on_exist)
    except RestoreCodeExist as e:
        raise ValidationError({'code': gettext_lazy(str(e))})
    else:
        return code


def get_sentinel_user():
    user, _ = get_user_model().objects.get_or_create(username="deleted")
    if user.is_active is True:
        user.is_active = False
        user.save()
    return user
