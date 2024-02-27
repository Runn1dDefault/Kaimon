from django.db.models.signals import post_save, post_delete
from django.dispatch import receiver

from .models import Category, ProductReview
from .tasks import update_product_reviews_data, delete_category_products, category_cache_clear


@receiver(post_save, sender=Category)
def on_save_category(sender, instance, created, **kwargs):
    if created:
        return

    if instance.deactivated:
        delete_category_products.delay(instance.id)

    category_cache_clear.delay()


@receiver(post_delete, sender=Category)
def on_delete_category(sender, instance, **kwargs):
    category_cache_clear.delay()


@receiver(post_save, sender=ProductReview)
def on_save_product_review(sender, instance, **kwargs):
    update_product_reviews_data.delay(instance.product.id)


@receiver(post_delete, sender=ProductReview)
def on_delete_product_review(sender, instance, **kwargs):
    update_product_reviews_data.delay(instance.product.id)
