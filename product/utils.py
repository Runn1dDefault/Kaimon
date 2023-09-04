from django.conf import settings
from django.utils.translation import gettext_lazy as _
from rest_framework.exceptions import ParseError


def round_half_integer(number):
    integer_part = int(number)
    decimal_part = number - integer_part

    if decimal_part < 0.3:
        rounded_decimal_part = 0
    elif decimal_part < 0.6:
        rounded_decimal_part = 0.5
    else:
        rounded_decimal_part = 1.0

    return integer_part + rounded_decimal_part


def get_genre_parents_tree(current_genre) -> list[int]:
    collected_parents = [current_genre.id]
    for fk_parent in current_genre.parents.all():
        collected_parents.extend(get_genre_parents_tree(fk_parent.parent))

    return collected_parents


def get_last_children(current_genre) -> list[int]:
    last_children = []

    for child in current_genre.children.all():
        if not child.children.exists():
            last_children.append(child.id)
            continue

        last_children.extend(get_last_children(child))
    return last_children


def get_field_by_lang(field_name: str, lang: str):
    if lang in settings.SUPPORTED_LANG:
        return f'{field_name}_{lang}' if lang != 'ja' else field_name
