from django.db.models import Count, Q

from kaimon.celery import app

from .models import Genre
from .utils import get_last_children


@app.task()
def deactivate_empty_genres():
    base_genres = Genre.objects.filter(level=1)
    to_full_deactivate = []

    for base_genre in base_genres:
        last_children_ids = get_last_children(base_genre)
        to_deactivate_genres = Genre.objects.filter(id__in=last_children_ids).annotate(
            products_qty=Count('products', filter=Q(products__is_active=True, products__availability=True))
        ).filter(products_qty=0)

        deactivated_rows = to_deactivate_genres.update(deactivated=True)
        if len(deactivated_rows) == last_children_ids:
            base_genre.deactivated = True
            to_full_deactivate.append(base_genre)

    if to_full_deactivate:
        Genre.objects.bulk_update(to_full_deactivate, ('deactivated',))
