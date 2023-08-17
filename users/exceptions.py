from rest_framework_simplejwt.exceptions import TokenError


class RestoreCodeExist(TokenError):
    pass


class InvalidRestoreCode(TokenError):
    pass
