from django.core.exceptions import ValidationError


def only_digit_validator(value: str):
    if value.isdigit() is False:
        raise ValidationError('must contains only digit')
