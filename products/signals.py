from django.db.models.signals import post_save, post_delete
from django.dispatch import receiver

from .models import Product, Category, ProductReview
from .tasks import update_product_reviews_data, products_cache_clear, categories_cache_clear


@receiver(post_save, sender=Product)
def cache_clear_on_update_product(sender, instance, created, **kwargs):
    if not created:
        products_cache_clear.delay()


@receiver(post_save, sender=Category)
def cache_clear_on_update_category(sender, instance, created, **kwargs):
    if not created:
        categories_cache_clear.delay()


@receiver(post_delete, sender=Product)
def cache_clear_on_delete_product(sender, instance, **kwargs):
    products_cache_clear.delay()


@receiver(post_delete, sender=Category)
def cache_clear_on_delete_category(sender, instance, **kwargs):
    categories_cache_clear.delay()


@receiver(post_save, sender=ProductReview)
def update_product_average_rank_on_create(sender, instance, created, **kwargs):
    update_product_reviews_data.delay(instance.product.id)


@receiver(post_delete, sender=ProductReview)
def update_product_average_rank_on_delete(sender, instance, **kwargs):
    update_product_reviews_data.delay(instance.product.id)
