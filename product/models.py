from django.db import models
from django.utils.translation import gettext_lazy as _


class Genre(models.Model):
    id = models.BigIntegerField(primary_key=True)
    level = models.PositiveIntegerField()

    name = models.CharField(max_length=255, blank=True, verbose_name=_('Name') + '[ja]')
    name_tr = models.CharField(max_length=255, blank=True, verbose_name=_('Name') + '[tr]')
    name_ru = models.CharField(max_length=255, blank=True, verbose_name=_('Name') + '[ru]')
    name_en = models.CharField(max_length=255, blank=True, verbose_name=_('Name') + '[en]')
    name_ky = models.CharField(max_length=255, blank=True, verbose_name=_('Name') + '[ky]')
    name_de = models.CharField(max_length=255, blank=True, verbose_name=_('Name') + '[de]')


class GenreChild(models.Model):
    parent = models.ForeignKey(Genre, on_delete=models.CASCADE, related_name='children')
    child = models.ForeignKey(Genre, on_delete=models.CASCADE, related_name='parents')


class Marker(models.Model):
    name = models.CharField(max_length=255, verbose_name=_('Name') + '[ja]', primary_key=True)
    url = models.URLField(max_length=1000, blank=True, null=True)

    name_tr = models.CharField(max_length=255, blank=True, verbose_name=_('Name') + '[tr]')
    name_ru = models.CharField(max_length=255, blank=True, verbose_name=_('Name') + '[ru]')
    name_en = models.CharField(max_length=255, blank=True, verbose_name=_('Name') + '[en]')
    name_ky = models.CharField(max_length=255, blank=True, verbose_name=_('Name') + '[ky]')
    name_de = models.CharField(max_length=255, blank=True, verbose_name=_('Name') + '[de]')


class Product(models.Model):
    # General Info
    rakuten_id = models.CharField(max_length=32, unique=True)
    number = models.CharField(max_length=50, blank=True)
    marker = models.ForeignKey(Marker, on_delete=models.SET_NULL, related_name='products', null=True, blank=True)
    marker_code = models.CharField(max_length=255, blank=True)

    name = models.CharField(max_length=500, verbose_name=_('Name') + '[ja]')
    name_tr = models.CharField(max_length=500, blank=True, verbose_name=_('Name') + '[tr]')
    name_ru = models.CharField(max_length=500, blank=True, verbose_name=_('Name') + '[ru]')
    name_en = models.CharField(max_length=500, blank=True, verbose_name=_('Name') + '[en]')
    name_ky = models.CharField(max_length=500, blank=True, verbose_name=_('Name') + '[ky]')
    name_de = models.CharField(max_length=500, blank=True, verbose_name=_('Name') + '[de]')

    description = models.TextField(blank=True, null=True, verbose_name=_('Description') + '[ja]')
    description_tr = models.TextField(blank=True, null=True, verbose_name=_('Description') + '[tr]')
    description_ru = models.TextField(blank=True, null=True, verbose_name=_('Description') + '[ru]')
    description_en = models.TextField(blank=True, null=True, verbose_name=_('Description') + '[en]')
    description_ky = models.TextField(blank=True, null=True, verbose_name=_('Description') + '[ky]')
    description_de = models.TextField(blank=True, null=True, verbose_name=_('Description') + '[de]')

    brand_name = models.CharField(max_length=255, blank=True)

    # Genres and rank
    genres = models.ManyToManyField(Genre, related_name='products', related_query_name='product')
    rank = models.IntegerField(null=True, blank=True)

    price = models.FloatField(null=True)

    count = models.PositiveIntegerField(null=True, blank=True)

    image_url = models.TextField(blank=True, null=True)
    product_url = models.TextField(blank=True, null=True)

    release_date = models.DateField()
    created_at = models.DateTimeField(auto_now_add=True)
    modified_at = models.DateTimeField(auto_now=True)


class ProductDetail(models.Model):
    product = models.ForeignKey(Product, on_delete=models.CASCADE, related_name='details')
    name = models.CharField(max_length=500, verbose_name=_('Name') + '[ja]')
    name_tr = models.CharField(max_length=500, blank=True, verbose_name=_('Name') + '[tr]')
    name_ru = models.CharField(max_length=500, blank=True, verbose_name=_('Name') + '[ru]')
    name_en = models.CharField(max_length=500, blank=True, verbose_name=_('Name') + '[en]')
    name_ky = models.CharField(max_length=500, blank=True, verbose_name=_('Name') + '[ky]')
    name_de = models.CharField(max_length=500, blank=True, verbose_name=_('Name') + '[de]')

    value = models.TextField(blank=True, null=True, verbose_name=_('Value') + '[ja]')
    value_tr = models.TextField(blank=True, null=True, verbose_name=_('Value') + '[tr]')
    value_ru = models.TextField(blank=True, null=True, verbose_name=_('Value') + '[ru]')
    value_en = models.TextField(blank=True, null=True, verbose_name=_('Value') + '[en]')
    value_ky = models.TextField(blank=True, null=True, verbose_name=_('Value') + '[ky]')
    value_de = models.TextField(blank=True, null=True, verbose_name=_('Value') + '[de]')
