from typing import Iterable

from django.db import connection

from product.models import Genre


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


def check_all_genres_active(genre_ids: Iterable[int]) -> bool:
    genre_ids = set(genre_ids)
    genres = Genre.objects.filter(id__in=genre_ids, deactivated=False)
    return genres.count() == len(genre_ids)


def filter_only_active_genres(genre_ids: Iterable[int]):
    return Genre.objects.filter(id__in=genre_ids, deactivated=False)
