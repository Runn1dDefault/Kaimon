from django.core.exceptions import ObjectDoesNotExist
from django.db.models import Avg

from kaimon.celery import app

from .models import Product, ProductInventory


@app.task()
def update_product_reviews_data(product_id):
    product = Product.objects.prefetch_related('reviews').get(id=product_id)
    product.reviews_count = product.reviews.filter(moderated=True).count()
    product.avg_rating = product.reviews.filter(moderated=True).aggregate(Avg('rating'))['rating__avg']
    product.save()


@app.task()
def update_product_sale_price(product_id: int):
    product = Product.objects.get(id=product_id)
    inventories = product.inventories.all()
    update_inventories = []

    promotion = product.promotions.active_promotions().first()
    if not promotion:
        inventories.update(sale_price=0.0)
        return

    try:
        discount = promotion.discount
    except ObjectDoesNotExist:
        inventories.update(sale_price=0.0)
        return

    for inventory in inventories:
        inventory.sale_price = None
        if inventory.price and inventory.price > 0:
            inventory.sale_price = discount.calc_price(product.price)
        update_inventories.append(inventory)

    if update_inventories:
        ProductInventory.objects.bulk_update(update_inventories, fields={'sale_price'})


@app.task()
def test():
    print('Hello world')
