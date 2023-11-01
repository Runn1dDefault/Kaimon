from django.db.models.signals import post_save, post_delete
from django.dispatch import receiver

from promotions.models import Discount


@receiver(post_save, sender=Discount)
def update_products_sale_prices(sender, instance, created, **kwargs):
    products = instance.promotion.products.filter(is_active=True)
    for product in products:
        product.update_sale_price()


@receiver(post_delete, sender=Discount)
def update_product_average_rank_on_delete(sender, instance, **kwargs):
    products = instance.promotion.products.filter(is_active=True)
    for product in products:
        product.update_sale_price()
