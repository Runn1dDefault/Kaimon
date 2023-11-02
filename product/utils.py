import uuid

from django.conf import settings
from django.db import connection


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


def get_tags_for_product(product_id) -> list[dict[str, int | str]]:
    with connection.cursor() as cursor:
        cursor.execute(
            """
            SELECT t.id as tag_id, t.name as tag_name, t.group_id as group_id, tg.name as group_name
              FROM product_tag as t
            JOIN product_taggroup as tg ON (t.group_id = tg.id)
            INNER JOIN product_product_tags as pt ON (t.id = pt.tag_id)
            WHERE pt.product_id = %s
            """, (product_id,)
        )
        columns = [col[0] for col in cursor.description]
        rows = [dict(zip(columns, row)) for row in cursor.fetchall()]

    collected_data = {}
    for row in rows:
        group_id = row['group_id']
        if group_id not in collected_data:
            collected_data[group_id] = {
                'group_id': group_id,
                'group_name': row['group_name'],
                'tags': []
            }
        collected_data[group_id]['tags'].append(
            {'id': row['tag_id'], 'name': row['tag_name']}
        )
    return list(collected_data.values())
