from typing import Self

from django.conf import settings
from django.contrib.auth import get_user_model
from django.core.validators import MaxValueValidator, MinValueValidator
from django.db import models
from django.db.models import Q
from django.utils.translation import gettext_lazy as _

from utils.helpers import round_half_integer, internal_uid_generation, increase_price

from .querysets import TagGroupQuerySet, ReviewAnalyticsQuerySet


class Site(models.TextChoices):
    rakuten = 'rakuten', _('Rakuten')
    uniqlo = 'uniqlo', _('Uniqlo')

    @classmethod
    def from_string(cls, site: str) -> Self | None:
        for attr, choice in cls.choices:
            if choice == site:
                return getattr(cls, attr)


class BaseSiteModel(models.Model):
    objects = models.Manager()
    site = models.CharField(choices=Site.choices, default=Site.rakuten)
    site_id = models.BigIntegerField()

    class Meta:
        abstract = True


class Genre(BaseSiteModel):
    level = models.PositiveIntegerField(null=True, blank=True)
    name = models.CharField(max_length=100)

    deactivated = models.BooleanField(default=False, null=True)
    parent = models.ForeignKey('self', on_delete=models.SET_NULL, related_name='children', null=True, blank=True)
    avg_weight = models.FloatField(null=True, blank=True)
    fedex_description = models.CharField(null=True, blank=True)

    def __str__(self):
        return str(self.id)

    class Meta:
        unique_together = ('site', 'site_id')
        indexes = (
            models.Index(name='exclude_zero_idx', fields=('name',), condition=~Q(level=0), include=('level',)),
            models.Index(name='activate_genres_idx', fields=('name',), condition=Q(deactivated=False),
                         include=('deactivated',)),
        )


class BaseTagModel(BaseSiteModel):
    name = models.CharField(max_length=100)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        abstract = True


class TagGroup(BaseTagModel):
    objects = TagGroupQuerySet.as_manager()

    def __str__(self):
        return f'Group: {self.id}'

    class Meta:
        unique_together = ('site', 'site_id')


class Tag(BaseTagModel):
    group = models.ForeignKey(TagGroup, on_delete=models.CASCADE, related_name='tags', null=True)

    def __str__(self):
        if self.group:
            return f'{self.group} Tag: {self.id}'
        return f'Tag: {self.id}'

    class Meta:
        unique_together = ('site', 'site_id')


class Product(BaseSiteModel):
    site_id = models.CharField(max_length=255, unique=True, default=internal_uid_generation)
    # Product Info
    name = models.CharField(max_length=255, verbose_name=_('Name') + '[ja]')
    description = models.TextField(blank=True, null=True, verbose_name=_('Description') + '[ja]')
    site_price = models.DecimalField(max_digits=20, decimal_places=10, validators=[MinValueValidator(limit_value=1)])
    increase_percentage = models.FloatField(default=settings.DEFAULT_INCREASE_PRICE_PER,
                                            validators=[MaxValueValidator(limit_value=100),
                                                        MinValueValidator(limit_value=0)])
    product_url = models.TextField(blank=True, null=True)
    availability = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    modified_at = models.DateTimeField(auto_now=True)
    is_active = models.BooleanField(default=True)

    avg_rank = models.FloatField(default=0)
    receipts_qty = models.PositiveIntegerField(default=0)
    reviews_count = models.PositiveIntegerField(default=0)
    sale_price = models.DecimalField(max_digits=20, decimal_places=10, null=True, default=None)

    genres = models.ManyToManyField(Genre, related_name='products', db_table='product_product_genres')
    tags = models.ManyToManyField(Tag, related_name='products', db_table='product_product_tags')

    @property
    def price(self):
        return increase_price(self.site_price, self.increase_percentage)

    class Meta:
        unique_together = ('site', 'site_id')
        indexes = (
            models.Index(fields=('avg_rank',)),
            models.Index(fields=('created_at',)),
            models.Index(fields=('reviews_count',)),
            models.Index(fields=('receipts_qty',)),
            models.Index(name='available_idx', fields=('name',), condition=Q(availability=True),
                         include=['availability'])
        )


class ProductImageUrl(models.Model):
    objects = models.Manager()
    product = models.ForeignKey(Product, on_delete=models.CASCADE, related_name='image_urls')
    url = models.TextField()

    def __str__(self):
        return self.url

    class Meta:
        indexes = (models.Index(fields=('product', 'url')),)


class ProductReview(models.Model):
    analytics = ReviewAnalyticsQuerySet.as_manager()
    objects = models.Manager()

    user = models.ForeignKey(get_user_model(), on_delete=models.CASCADE, related_name='reviews')
    product = models.ForeignKey(Product, on_delete=models.CASCADE, related_name='reviews')
    rank = models.FloatField(validators=[MinValueValidator(0), MaxValueValidator(5)], default=0)
    comment = models.TextField(blank=True, null=True)
    is_active = models.BooleanField(default=True)
    is_read = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    modified_at = models.DateTimeField(auto_now=True)

    def save(
        self, force_insert=False, force_update=False, using=None, update_fields=None
    ):
        self.rank = round_half_integer(self.rank)
        super().save(force_insert=force_insert, force_update=force_update, update_fields=update_fields)
