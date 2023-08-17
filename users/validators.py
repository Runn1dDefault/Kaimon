from django.core.exceptions import ValidationError
from django.utils.translation import gettext_lazy


def validate_full_name(value: str):
    if len(value.split()) != 2:
        raise ValidationError(gettext_lazy('full_name must contains two params: first_name last_name'))
