import uuid

from django.conf import settings


def internal_product_id_generation():
    return 'internal:' + str(uuid.uuid4())


def get_genre_parents_tree(current_genre) -> list[int]:
    collected_parents = [current_genre.id]
    if not current_genre.parent:
        return collected_parents
    collected_parents.extend(get_genre_parents_tree(current_genre.parent))
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
