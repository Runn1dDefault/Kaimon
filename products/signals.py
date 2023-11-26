from django.db.models.signals import post_save, post_delete
from django.dispatch import receiver

from .models import Product, ProductInventory, Category, ProductReview
from .tasks import update_product_reviews_data
from .views import ProductsViewSet, CategoryViewSet


@receiver(post_save, sender=Product)
def on_save_product(sender, instance, created, **kwargs):
    ProductsViewSet.cache_clear()


@receiver(post_save, sender=Category)
def on_save_category(sender, instance, created, **kwargs):
    CategoryViewSet.cache_clear()
    if not created:
        instance.products.update(is_active=not instance.deactivated)


@receiver(post_delete, sender=Product)
def on_delete_product(**kwargs):
    ProductsViewSet.cache_clear()


@receiver(post_delete, sender=Category)
def on_delete_category(**kwargs):
    CategoryViewSet.cache_clear()


@receiver(post_save, sender=ProductReview)
def on_save_product_review(sender, instance, **kwargs):
    update_product_reviews_data.delay(instance.product.id)


@receiver(post_delete, sender=ProductReview)
def on_delete_product_review(sender, instance, **kwargs):
    update_product_reviews_data.delay(instance.product.id)
