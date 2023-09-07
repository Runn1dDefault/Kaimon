from django.contrib.auth import get_user_model
from django.core.validators import MaxValueValidator, MinValueValidator
from django.db import models
from django.utils.translation import gettext_lazy as _

from product.querysets import GenreQuerySet, ProductQuerySet, TagQuerySet
from product.utils import round_half_integer


class Genre(models.Model):
    objects = GenreQuerySet.as_manager()

    id = models.BigIntegerField(primary_key=True)
    level = models.PositiveIntegerField(null=True, blank=True)

    name = models.CharField(max_length=255, blank=True, null=True, verbose_name=_('Name') + '[ja]')
    name_ru = models.CharField(max_length=255, blank=True, null=True, verbose_name=_('Name') + '[ru]')
    name_en = models.CharField(max_length=255, blank=True, null=True, verbose_name=_('Name') + '[en]')
    name_tr = models.CharField(max_length=255, blank=True, null=True, verbose_name=_('Name') + '[tr]')
    name_ky = models.CharField(max_length=255, blank=True, null=True, verbose_name=_('Name') + '[ky]')
    name_kz = models.CharField(max_length=255, blank=True, null=True, verbose_name=_('Name') + '[kz]')

    deactivated = models.BooleanField(default=False, null=True)
    parent = models.ForeignKey('self', on_delete=models.SET_NULL, related_name='children', null=True)

    def __str__(self):
        return str(self.id)


class BaseTagModel(models.Model):
    id = models.BigIntegerField(primary_key=True)
    name = models.CharField(max_length=255)
    name_tr = models.CharField(max_length=500, blank=True, null=True, verbose_name=_('Name') + '[tr]')
    name_ru = models.CharField(max_length=500, blank=True, null=True, verbose_name=_('Name') + '[ru]')
    name_en = models.CharField(max_length=500, blank=True, null=True, verbose_name=_('Name') + '[en]')
    name_ky = models.CharField(max_length=500, blank=True, null=True, verbose_name=_('Name') + '[ky]')
    name_kz = models.CharField(max_length=500, blank=True, null=True, verbose_name=_('Name') + '[kz]')
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        abstract = True


class TagGroup(BaseTagModel):
    objects = TagQuerySet.as_manager()

    def __str__(self):
        return f'Tag-group-{self.id}-{self.name}'


class Tag(BaseTagModel):
    group = models.ForeignKey(TagGroup, on_delete=models.CASCADE, related_name='tags', null=True, blank=True)

    def __str__(self):
        if self.group:
            return f'#{self.group.name}-{self.id}-{self.name}'
        return f'#{self.id}-{self.name}'


class Product(models.Model):
    objects = ProductQuerySet.as_manager()
    id = models.CharField(max_length=255, primary_key=True)
    # Product Info
    name = models.CharField(max_length=255, verbose_name=_('Name') + '[ja]')
    description = models.TextField(blank=True, null=True, verbose_name=_('Description') + '[ja]')
    price = models.FloatField(null=True)
    product_url = models.TextField(blank=True, null=True)
    availability = models.BooleanField(default=True)
    # Genres and tags
    # Why ManyToManyField? is about making it accessible from the top level of genres.
    # Without wasting filtering operations
    genres = models.ManyToManyField(
        Genre,
        blank=True,
        related_name="product_set",
        related_query_name="product",
    )
    tags = models.ManyToManyField(
        Tag,
        blank=True,
        related_name='product_set',
        related_query_name='product'
    )
    created_at = models.DateTimeField(auto_now_add=True)
    modified_at = models.DateTimeField(auto_now=True)
    is_active = models.BooleanField(default=True)
    reference_rank = models.IntegerField(null=True, blank=True)

    # translating fields
    name_tr = models.CharField(max_length=255, blank=True, null=True, verbose_name=_('Name') + '[tr]')
    name_ru = models.CharField(max_length=255, blank=True, null=True, verbose_name=_('Name') + '[ru]')
    name_en = models.CharField(max_length=255, blank=True, null=True, verbose_name=_('Name') + '[en]')
    name_ky = models.CharField(max_length=255, blank=True, null=True, verbose_name=_('Name') + '[ky]')
    name_kz = models.CharField(max_length=255, blank=True, null=True, verbose_name=_('Name') + '[kz]')
    description_tr = models.TextField(blank=True, null=True, verbose_name=_('Description') + '[tr]')
    description_ru = models.TextField(blank=True, null=True, verbose_name=_('Description') + '[ru]')
    description_en = models.TextField(blank=True, null=True, verbose_name=_('Description') + '[en]')
    description_ky = models.TextField(blank=True, null=True, verbose_name=_('Description') + '[ky]')
    description_kz = models.TextField(blank=True, null=True, verbose_name=_('Description') + '[kz]')


class ProductImageUrl(models.Model):
    product = models.ForeignKey(Product, on_delete=models.CASCADE, related_name='image_urls')
    url = models.TextField()

    def __str__(self):
        return self.url


class ProductReview(models.Model):
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
