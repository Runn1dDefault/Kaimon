import logging
import time

from django.core.exceptions import ObjectDoesNotExist
from django.db.models import Avg

from kaimon.celery import app
from service.utils import get_translated_text, is_japanese_char

from .models import Product, ProductInventory, Tag, Category
from .views import CategoryViewSet, ProductsViewSet


@app.task()
def category_cache_clear():
    CategoryViewSet.cache_clear()


@app.task()
def products_cache_clear():
    ProductsViewSet.cache_clear()


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
        inventories.update(sale_price=None)
        return

    try:
        discount = promotion.discount
    except ObjectDoesNotExist:
        inventories.update(sale_price=None)
        return

    for inventory in inventories:
        inventory.sale_price = None
        if inventory.price and inventory.price > 0:
            inventory.sale_price = discount.calc_price(product.price)
        update_inventories.append(inventory)

    if update_inventories:
        ProductInventory.objects.bulk_update(update_inventories, fields={'sale_price'})


@app.task()
def translated_tag_group(group_id):
    group = Tag.objects.get(id=group_id)
    select_lang, target_lang = 'ja', 'en'
    group.name = get_translated_text(select_lang, target_lang, group.name)
    group.save()

    updated_tags = []

    for tag in group.children.all():
        if not is_japanese_char(tag.name):
            continue

        try:
            tag.name = get_translated_text(select_lang, target_lang, tag.name)
        except Exception as e:
            logging.error(e)
            time.sleep(10)
            continue

        updated_tags.append(tag)

    if updated_tags:
        Tag.objects.bulk_update(updated_tags, fields=("name",))


@app.task()
def update_category_products_activity(category_id):
    category = Category.objects.get(id=category_id)
    category.products.update(is_active=not category.deactivated)

