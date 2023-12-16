from django.db.models.signals import post_save, pre_delete
from django.dispatch import receiver

from promotions.models import Discount
from products.tasks import update_product_sale_price


@receiver(post_save, sender=Discount)
def update_products_sale_prices(sender, instance, created, **kwargs):
    product_ids = instance.promotion.products.filter(is_active=True).values_list('id', flat=True)
    for product_id in product_ids:
        update_product_sale_price.delay(product_id)


@receiver(pre_delete, sender=Discount)
def update_product_average_rank_on_delete(sender, instance, **kwargs):
    product_ids = instance.promotion.products.filter(is_active=True).values_list('id', flat=True)
    for product_id in product_ids:
        update_product_sale_price.delay(product_id)
