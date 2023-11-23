from django.db.models.signals import post_save, post_delete
from django.dispatch import receiver

from orders.models import Receipt, Order
from orders.tasks import update_order_shipping_details, create_order_conversions


@receiver(post_save, sender=Order)
def create_order_details(sender, instance, created, **kwargs):
    if created:
        create_order_conversions.delay(instance.id)
        update_order_shipping_details.delay(instance.id)


@receiver(post_save, sender=Receipt)
def update_order_total_price(sender, instance, created, **kwargs):
    if not created:
        update_order_shipping_details.delay(instance.order.id)


@receiver(post_delete, sender=Receipt)
def update_product_average_rank_on_delete(sender, instance, **kwargs):
    update_order_shipping_details.delay(instance.order.id)
