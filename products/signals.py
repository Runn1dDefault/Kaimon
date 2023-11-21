from django.db.models.signals import post_save, post_delete
from django.dispatch import receiver

from products.models import ProductReview
from products.tasks import update_product_reviews_data


@receiver(post_save, sender=ProductReview)
def update_product_average_rank_on_create(sender, instance, created, **kwargs):
    update_product_reviews_data.delay(instance.product.id)


@receiver(post_delete, sender=ProductReview)
def update_product_average_rank_on_delete(sender, instance, **kwargs):
    update_product_reviews_data.delay(instance.product.id)
