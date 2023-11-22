from django.core.validators import MaxValueValidator
from django.db import models
from django.utils.translation import gettext_lazy as _

from products.models import Product
from promotions.querysets import PromotionQueryset


class Banner(models.Model):
    objects = models.Manager()

    name = models.CharField(max_length=255, verbose_name=_('Name') + '[ja]')
    description = models.TextField(blank=True, null=True, verbose_name=_('Description') + '[ja]')
    image = models.ImageField(upload_to='banners/', null=True, blank=True)

    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.name


class Promotion(models.Model):
    objects = PromotionQueryset.as_manager()

    banner = models.ForeignKey(Banner, on_delete=models.CASCADE, related_name='promotions')
    products = models.ManyToManyField(
        Product,
        blank=True,
        related_name="promotions",
        related_query_name="promotion"
    )
    deactivated = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)


class Discount(models.Model):
    objects = models.Manager()

    # pulled out into a separate model,
    # since in the future they may add a different kind of promotion that does not use discount
    promotion = models.OneToOneField(Promotion, on_delete=models.CASCADE, primary_key=True)
    percentage = models.DecimalField(max_digits=5, decimal_places=2, validators=[MaxValueValidator(100)])

    def calc_price(self, price: float | int):
        if price <= 0:
            return 0
        return price - (self.percentage * price / 100)

    def __str__(self):
        return str(self.percentage)
