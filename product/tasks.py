from django.core.exceptions import ObjectDoesNotExist
from django.db.models import Count, Q, Avg

from kaimon.celery import app

from .models import Genre, Product
from .utils import get_last_children


@app.task()
def update_product_reviews_data(product_id):
    product = Product.objects.prefetch_related('reviews').get(id=product_id)
    product.reviews_count = product.reviews.filter(is_active=True).values('id').distinct().count() or 0
    product.avg_rank = product.reviews.filter(is_active=True).aggregate(Avg('rank'))['rank__avg']
    product.save()


@app.task()
def update_product_receipts_qty(product_id):
    product = Product.objects.prefetch_related('receipts').get(id=product_id)
    product.receipts_qty = product.receipts.values('order_id').distinct().count() or 0
    product.save()


@app.task()
def update_product_sale_price(product_id: int):
    product = Product.objects.get(id=product_id)

    product.sale_price = None
    if not product.availability or not product.price or product.price <= 0:
        product.save()
        return

    promotion = product.promotions.active_promotions().first()
    if not promotion:
        product.save()
        return

    try:
        discount = promotion.discount
    except ObjectDoesNotExist:
        # in the future here can be changed, when new promotion logic will be added
        return None

    product.sale_price = discount.calc_price(product.price)
    product.save()


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


@app.task()
def deactivate_products():
    deactivated_genres = Genre.objects.filter(deactivated=True)
    if not deactivated_genres:
        return

    for genre in deactivated_genres:
        genre.products.update(is_active=False)

