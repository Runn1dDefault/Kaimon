from django.db.models.signals import post_save, post_delete
from django.dispatch import receiver

from .models import Category, ProductReview
from .tasks import update_product_reviews_data, update_category_products_activity


@receiver(post_save, sender=Category)
def on_save_category(sender, instance, created, **kwargs):
    if not created:
        update_category_products_activity.delay(instance.id)


@receiver(post_save, sender=ProductReview)
def on_save_product_review(sender, instance, **kwargs):
    update_product_reviews_data.delay(instance.product.id)


@receiver(post_delete, sender=ProductReview)
def on_delete_product_review(sender, instance, **kwargs):
    update_product_reviews_data.delay(instance.product.id)
