from django.db.models.signals import post_save, post_delete
from django.dispatch import receiver

from product.models import ProductReview


@receiver(post_save, sender=ProductReview)
def update_product_average_rank_on_create(sender, instance, created, **kwargs):
    instance.product.update_average_rank()
    instance.product.update_reviews_count()


@receiver(post_delete, sender=ProductReview)
def update_product_average_rank_on_delete(sender, instance, **kwargs):
    instance.product.update_average_rank()
    instance.product.update_reviews_count()
