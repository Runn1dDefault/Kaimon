from django.contrib.auth import get_user_model
from django.core.validators import MaxValueValidator, MinValueValidator
from django.db import models
from django.utils.translation import gettext_lazy as _

from product.querysets import GenreQuerySet, ProductQuerySet
from product.utils import round_half_integer


class Genre(models.Model):
    objects = GenreQuerySet.as_manager()

    id = models.BigIntegerField(primary_key=True)
    level = models.PositiveIntegerField(null=True, blank=True)

    name = models.CharField(max_length=255, blank=True, null=True, verbose_name=_('Name') + '[ja]')
    name_ky = models.CharField(max_length=255, blank=True, null=True, verbose_name=_('Name') + '[ky]')
    name_ru = models.CharField(max_length=255, blank=True, null=True, verbose_name=_('Name') + '[ru]')
    name_en = models.CharField(max_length=255, blank=True, null=True, verbose_name=_('Name') + '[en]')
    name_tr = models.CharField(max_length=255, blank=True, null=True, verbose_name=_('Name') + '[tr]')
    name_kz = models.CharField(max_length=255, blank=True, null=True, verbose_name=_('Name') + '[kz]')

    deactivated = models.BooleanField(default=False, null=True)

    def __str__(self):
        return f'{self.id}{self.name}'


class GenreChild(models.Model):
    parent = models.ForeignKey(Genre, on_delete=models.CASCADE, related_name='children')
    child = models.ForeignKey(Genre, on_delete=models.CASCADE, related_name='parents')

    class Meta:
        verbose_name_plural = _('GenreChildren')


class Marker(models.Model):
    name = models.CharField(max_length=255, verbose_name=_('Name') + '[ja]', primary_key=True)
    rakuten_code = models.CharField(max_length=255, blank=True, null=True)
    url = models.URLField(max_length=1000, blank=True, null=True)

    name_tr = models.CharField(max_length=255, blank=True, null=True, verbose_name=_('Name') + '[tr]')
    name_ru = models.CharField(max_length=255, blank=True, null=True, verbose_name=_('Name') + '[ru]')
    name_en = models.CharField(max_length=255, blank=True, null=True, verbose_name=_('Name') + '[en]')
    name_ky = models.CharField(max_length=255, blank=True, null=True, verbose_name=_('Name') + '[ky]')
    name_kz = models.CharField(max_length=255, blank=True, null=True, verbose_name=_('Name') + '[kz]')


class Product(models.Model):
    objects = ProductQuerySet.as_manager()

    # General Info
    rakuten_id = models.CharField(max_length=32, unique=True)
    number = models.CharField(max_length=50, blank=True)
    marker = models.ForeignKey(Marker, on_delete=models.SET_NULL, related_name='products', null=True, blank=True)
    marker_code = models.CharField(max_length=255, blank=True)

    name = models.CharField(max_length=500, verbose_name=_('Name') + '[ja]')
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

    brand_name = models.CharField(max_length=255, blank=True, null=True, verbose_name=_('Brand Name') + '[ja]')
    brand_name_tr = models.CharField(max_length=255, blank=True, null=True, verbose_name=_('Brand Name') + '[tr]')
    brand_name_ru = models.CharField(max_length=255, blank=True, null=True, verbose_name=_('Brand Name') + '[ru]')
    brand_name_en = models.CharField(max_length=255, blank=True, null=True, verbose_name=_('Brand Name') + '[en]')
    brand_name_ky = models.CharField(max_length=255, blank=True, null=True, verbose_name=_('Brand Name') + '[ky]')
    brand_name_kz = models.CharField(max_length=255, blank=True, null=True, verbose_name=_('Brand Name') + '[kz]')

    # Genres and rank
    # Why ManyToManyField? is about making it accessible from the top level of genres.
    # Without wasting filtering operations
    genres = models.ManyToManyField(
        Genre,
        blank=True,
        related_name="product_set",
        related_query_name="product",
    )
    rank = models.IntegerField(null=True, blank=True)

    price = models.FloatField(null=True)

    count = models.PositiveIntegerField(null=True, blank=True)

    image_url = models.TextField(blank=True, null=True)
    product_url = models.TextField(blank=True, null=True)

    release_date = models.DateField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    modified_at = models.DateTimeField(auto_now=True)
    is_active = models.BooleanField(default=True)

    def __str__(self):
        return f'{self.id}-{self.rakuten_id}'


class ProductDetail(models.Model):
    product = models.ForeignKey(Product, on_delete=models.CASCADE, related_name='details')
    name = models.CharField(max_length=500, verbose_name=_('Name') + '[ja]')
    name_ky = models.CharField(max_length=500, blank=True, null=True, verbose_name=_('Name') + '[ky]')
    name_ru = models.CharField(max_length=500, blank=True, null=True, verbose_name=_('Name') + '[ru]')
    name_en = models.CharField(max_length=500, blank=True, null=True, verbose_name=_('Name') + '[en]')
    name_tr = models.CharField(max_length=500, blank=True, null=True, verbose_name=_('Name') + '[tr]')
    name_kz = models.CharField(max_length=500, blank=True, null=True, verbose_name=_('Name') + '[kz]')

    value = models.TextField(blank=True, null=True, verbose_name=_('Value') + '[ja]')
    value_tr = models.TextField(blank=True, null=True, verbose_name=_('Value') + '[tr]')
    value_ru = models.TextField(blank=True, null=True, verbose_name=_('Value') + '[ru]')
    value_en = models.TextField(blank=True, null=True, verbose_name=_('Value') + '[en]')
    value_ky = models.TextField(blank=True, null=True, verbose_name=_('Value') + '[ky]')
    value_kz = models.TextField(blank=True, null=True, verbose_name=_('Value') + '[kz]')


class ProductReview(models.Model):
    user = models.ForeignKey(get_user_model(), on_delete=models.CASCADE, related_name='product_reviews')
    product = models.ForeignKey(Product, on_delete=models.CASCADE, related_name='reviews')
    rank = models.FloatField(validators=[MinValueValidator(0), MaxValueValidator(5)], default=0)
    comment = models.TextField(blank=True, null=True)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    modified_at = models.DateTimeField(auto_now=True)

    def save(
        self, force_insert=False, force_update=False, using=None, update_fields=None
    ):
        self.rank = round_half_integer(self.rank)
        super().save(force_insert=force_insert, force_update=force_update, update_fields=update_fields)
