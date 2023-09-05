from django.db import models
from django.db.models import Count
from django.utils import timezone


class PromotionQueryset(models.QuerySet):
    def with_active_products_qty(self):
        return self.annotate(products_count=Count('products', filter=models.Q(products__is_active=True)))

    def active_promotions(self):
        today = timezone.now()
        return self.with_active_products_qty().filter(products_count__gt=0, deactivated=False).filter(
            models.Q(start_date__lte=today, end_date__gt=today) |
            models.Q(start_date__isnull=True) |
            models.Q(end_date__isnull=True)
        )
