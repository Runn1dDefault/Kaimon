from django.core.exceptions import ObjectDoesNotExist
from django.db.models import Avg

from kaimon.celery import app

from .models import Genre, Product


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


# @app.task()
# def deactivate_products():
#     deactivated_genres = Genre.objects.filter(deactivated=True)
#     if not deactivated_genres:
#         return
#
#     for genre in deactivated_genres:
#         genre.products.update(is_active=False)

@app.task()
def deactivate_products():
    genres = Genre.objects.prefetch_related('products').filter(level=1, deactivated=True)
    update_products = []
    collected_ids = set()

    for genre in genres:
        for product in genre.products.all():
            if product.id in collected_ids:
                continue

            product.is_active = False
            update_products.append(product)
            collected_ids.add(product.id)

    if update_products:
        Product.objects.bulk_update(update_products, fields=['is_active'])
