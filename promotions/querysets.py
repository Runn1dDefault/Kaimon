from django.db import models
from django.db.models import Count
from django.utils import timezone


class PromotionQueryset(models.QuerySet):
    def with_active_products_qty(self):
        return self.annotate(products_count=Count('products', filter=models.Q(products__is_active=True)))

    def active_promotions(self):
        return self.filter(deactivated=False)
