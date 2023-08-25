from django.conf import settings
from django.utils.translation import gettext_lazy as _
from rest_framework.exceptions import ParseError


def get_genre_parents_tree(current_genre) -> list[int]:
    collected_parents = [current_genre.id]
    for fk_parent in current_genre.parents.all():
        collected_parents.extend(get_genre_parents_tree(fk_parent.parent))

    return collected_parents


def get_last_children(current_genre) -> list[int]:
    last_children = []

    for fk_child in current_genre.children.all():
        child = fk_child.child
        if not child.children.exists():
            last_children.append(child.id)
            continue

        last_children.extend(get_last_children(child))
    return last_children


def get_request_lang(request):
    lang = str(request.query_params.get(settings.LANGUAGE_QUERY, 'ja')).lower()
    if lang not in settings.SUPPORTED_LANG:
        raise ParseError(detail=_("Language %s does not support!") % lang)
    return lang


def get_field_by_lang(field_name: str, lang: str):
    if lang in settings.SUPPORTED_LANG:
        return f'{field_name}_{lang}' if lang != 'ja' else field_name
