from django.core.validators import MaxValueValidator
from django.db import models
from django.utils.translation import gettext_lazy as _

from product.models import Product


class Promotion(models.Model):
    name = models.CharField(max_length=255, verbose_name=_('Name') + '[ja]')
    name_tr = models.CharField(max_length=500, blank=True, null=True, verbose_name=_('Name') + '[tr]')
    name_ru = models.CharField(max_length=500, blank=True, null=True, verbose_name=_('Name') + '[ru]')
    name_en = models.CharField(max_length=500, blank=True, null=True, verbose_name=_('Name') + '[en]')
    name_ky = models.CharField(max_length=500, blank=True, null=True, verbose_name=_('Name') + '[ky]')
    name_kz = models.CharField(max_length=500, blank=True, null=True, verbose_name=_('Name') + '[kz]')

    description = models.TextField(blank=True, null=True, verbose_name=_('Description') + '[ja]')
    description_tr = models.TextField(blank=True, null=True, verbose_name=_('Description') + '[tr]')
    description_ru = models.TextField(blank=True, null=True, verbose_name=_('Description') + '[ru]')
    description_en = models.TextField(blank=True, null=True, verbose_name=_('Description') + '[en]')
    description_ky = models.TextField(blank=True, null=True, verbose_name=_('Description') + '[ky]')
    description_kz = models.TextField(blank=True, null=True, verbose_name=_('Description') + '[kz]')

    banner = models.ImageField(upload_to='banners/', null=True, blank=True)
    products = models.ManyToManyField(
        Product,
        blank=True,
        null=True,
        related_name="promotions",
        related_query_name="promotion",
    )
    start_date = models.DateField()
    end_date = models.DateField()
    created_at = models.DateTimeField(auto_now_add=True)


class Discount(models.Model):
    promotion = models.ForeignKey(Promotion, on_delete=models.CASCADE, related_name='discounts')
    discount = models.FloatField()

    def calc_price(self, price: float | int):
        if price <= 0:
            return 0
        return price - (self.discount * price / 100)
