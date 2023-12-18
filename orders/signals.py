from django.db.models.signals import post_save
from django.dispatch import receiver

from orders.models import Order
from orders.tasks import create_order_shipping_details, create_order_conversions


@receiver(post_save, sender=Order)
def create_order_details(sender, instance, created, **kwargs):
    if created:
        create_order_conversions.delay(instance.id)
        create_order_shipping_details.delay(instance.id)
