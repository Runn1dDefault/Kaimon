from django.core.exceptions import ObjectDoesNotExist
from django.db.models import Avg

from kaimon.celery import app

from .models import Product
from .views import ProductsViewSet, CategoryViewSet


@app.task()
def update_product_reviews_data(product_id):
    product = Product.objects.prefetch_related('reviews').get(id=product_id)
    product.reviews_count = product.reviews.filter(moderated=True).count()
    product.avg_rating = product.reviews.filter(moderated=True).aggregate(Avg('rating'))['rating__avg']
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
def products_cache_clear():
    ProductsViewSet.cache_clear()


@app.task()
def categories_cache_clear():
    CategoryViewSet.cache_clear()
