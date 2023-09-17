import uuid

from django.conf import settings


def increase_price(price):
    return price + (settings.INCREASE_PRICE_PERCENTAGE * price / 100)


def internal_product_id_generation():
    """
    a function that returns a new uuid4 with the prefix internal: at the beginning.
    The prefix can be useful for separating manually created products from other ones
    """
    return 'internal:' + str(uuid.uuid4())


def get_genre_parents_tree(current_genre) -> list[int]:
    """
    recursive way to get all ancestors including the genre itself
    It is important to remember that with this approach we work from the bottom up.
     And we get a list from the category itself to the topmost parent
    """
    collected_parents = [current_genre.id]
    if not current_genre.parent:
        return collected_parents
    collected_parents.extend(get_genre_parents_tree(current_genre.parent))
    return collected_parents


def get_last_children(current_genre) -> list[int]:
    """
    recursive way to get children that are missing children
    """
    last_children = []

    for child in current_genre.children.all():
        if not child.children.exists():
            last_children.append(child.id)
            continue

        last_children.extend(get_last_children(child))
    return last_children
