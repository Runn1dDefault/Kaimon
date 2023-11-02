from django.db.models.signals import post_save, post_delete
from django.dispatch import receiver

from order.models import Receipt


@receiver(post_save, sender=Receipt)
def update_product_receipts_qty_on_create(sender, instance, created, **kwargs):
    if created:
        instance.product.update_receipts_qty()


@receiver(post_delete, sender=Receipt)
def update_product_receipts_qty_on_delete(sender, instance, **kwargs):
    instance.product.update_receipts_qty()