from django.db.models.signals import post_save, post_delete
from django.dispatch import receiver

from .models import Product, Category, ProductReview
from .tasks import update_product_reviews_data
from .views import ProductsViewSet, CategoryViewSet


@receiver(post_save, sender=Product)
def cache_clear_on_update_product(sender, instance, created, **kwargs):
    if not created:
        ProductsViewSet.cache_clear()


@receiver(post_save, sender=Category)
def on_update_category(sender, instance, created, **kwargs):
    if not created:
        CategoryViewSet.cache_clear()
        instance.products.update(is_active=not instance.deactivated)


@receiver(post_delete, sender=Product)
def cache_clear_on_delete_product(sender, instance, **kwargs):
    ProductsViewSet.cache_clear()


@receiver(post_delete, sender=Category)
def cache_clear_on_delete_category(sender, instance, **kwargs):
    CategoryViewSet.cache_clear()


@receiver(post_save, sender=ProductReview)
def update_product_average_rank_on_create(sender, instance, created, **kwargs):
    update_product_reviews_data.delay(instance.product.id)


@receiver(post_delete, sender=ProductReview)
def update_product_average_rank_on_delete(sender, instance, **kwargs):
    update_product_reviews_data.delay(instance.product.id)
