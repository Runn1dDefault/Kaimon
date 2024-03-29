from django.conf import settings
from django.contrib.postgres.aggregates import ArrayAgg
from django.core.validators import MaxValueValidator, MinValueValidator
from django.db import models
from django.db.models.functions import JSONObject, Round
from django.template.defaultfilters import truncatechars
from django.utils.translation import gettext_lazy as _

from service.querysets import BaseAnalyticsQuerySet, AnalyticsFilterBy
from service.utils import increase_price, uid_generate


class QuerySet(models.QuerySet):
    def filter_by_site(self, site: str):
        return self.filter(id__startswith=site)


class BaseModel(models.Model):
    objects = QuerySet.as_manager()

    id = models.CharField(primary_key=True, max_length=100, default=uid_generate)

    class Meta:
        abstract = True


class Category(BaseModel):
    name = models.CharField(max_length=100)
    level = models.PositiveIntegerField(default=0)
    deactivated = models.BooleanField(default=False)
    parent = models.ForeignKey('self', on_delete=models.SET_NULL, related_name='children', null=True, blank=True)
    avg_weight = models.FloatField(null=True)

    class Meta:
        verbose_name_plural = _('Categories')
        indexes = (
            models.Index(fields=("id", "name")),
            models.Index(fields=("id", "level")),
        )

    @property
    def short_name(self):
        return truncatechars(self.name, 10)

    def __str__(self):
        return f"{self.short_name} ({self.id})"


class TagQuerySet(QuerySet):
    def grouped_tags(self, tag_ids: list[str] = None):
        return self.values(
            tag_group_id=models.F('group_id'),
            tag_group_name=models.F('group__name')
        ).annotate(
            tags=ArrayAgg(
                JSONObject(
                    id=models.F('id'),
                    name=models.F('name')
                ),
                filter=models.Q(id__in=tag_ids) if tag_ids else None,
                distinct=True  # required
            )
        )


class Tag(BaseModel):
    collections = TagQuerySet.as_manager()

    name = models.CharField(max_length=100)
    group = models.ForeignKey('self', on_delete=models.CASCADE, related_name='children', null=True, blank=True)

    class Meta:
        indexes = (
            models.Index(fields=("id", "name")),
        )

    def __str__(self):
        if self.group:
            return f"{self.name} ({self.group.name})"
        return self.name


class Product(BaseModel):
    name = models.CharField(max_length=255)
    description = models.TextField(blank=True, null=True)
    site_avg_rating = models.FloatField(default=0)
    site_reviews_count = models.FloatField(default=0)
    can_choose_tags = models.BooleanField(default=False)

    categories = models.ManyToManyField(Category, related_name='products')
    # TODO: category = models.ForeignKey(Category, on_delete=models.CASCADE, related_name='products')
    # tags = models.ManyToManyField(Tag, blank=True, related_name='products')

    avg_rating = models.FloatField(default=0)
    reviews_count = models.PositiveIntegerField(default=0)

    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    modified_at = models.DateTimeField(auto_now=True)

    shop_code = models.CharField(max_length=100)
    shop_url = models.URLField(max_length=700)
    catch_copy = models.CharField(max_length=300, blank=True, null=True)

    def __str__(self):
        return self.id

    class Meta:
        indexes = (
            models.Index(fields=("id", "name")),
            models.Index(fields=("id", "is_active")),
            models.Index(fields=("id", "is_active", "name")),
            models.Index(fields=("id", "site_avg_rating", "site_reviews_count")),
            models.Index(fields=("id", "created_at"))
        )


class ProductImage(models.Model):
    objects = models.Manager()

    product = models.ForeignKey(Product, on_delete=models.CASCADE, related_name='images')
    image = models.ImageField(upload_to='products/', blank=True, null=True)
    url = models.URLField(max_length=700, blank=True, null=True)


class ProductInventory(BaseModel):
    product = models.ForeignKey(Product, on_delete=models.CASCADE, related_name='inventories')
    item_code = models.CharField(max_length=100)
    site_price = models.DecimalField(max_digits=20, decimal_places=2)
    product_url = models.URLField(max_length=700)
    name = models.CharField(max_length=255)
    tags = models.ManyToManyField(Tag, blank=True, related_name='product_inventories')
    quantity = models.PositiveIntegerField(null=True, blank=True)
    status_code = models.CharField(max_length=100, blank=True, null=True)
    increase_per = models.FloatField(
        default=settings.DEFAULT_INCREASE_PRICE_PER,
        validators=[
            MinValueValidator(limit_value=0),
            MaxValueValidator(limit_value=100)
        ]
    )
    sale_price = models.DecimalField(max_digits=20, decimal_places=2, null=True, blank=True)
    color_image = models.URLField(max_length=700, blank=True, null=True)

    @property
    def price(self):
        if self.increase_per <= 0:
            return self.sale_price
        return increase_price(self.site_price, self.increase_per)

    class Meta:
        indexes = (
            models.Index(fields=("id", "name")),
        )


class ReviewAnalyticsQuerySet(BaseAnalyticsQuerySet):
    def by_dates(self, by: AnalyticsFilterBy):
        return self.values(date=by.value('created_at')).annotate(
            info=ArrayAgg(
                JSONObject(
                    user_id=models.F('user__id'),
                    email=models.F('user__email'),
                    name=models.F('user__full_name'),
                    comment=models.F('comment'),
                    rating=models.F('rating'),
                    moderated=models.F('moderated')
                )
            ),
            count=models.Count('id'),
            avg_rating=Round(models.Avg('rating'), precision=1)
        )


class ProductReview(models.Model):
    objects = models.Manager()
    analytics = ReviewAnalyticsQuerySet.as_manager()

    user = models.ForeignKey('users.User', on_delete=models.CASCADE, related_name='product_reviews')
    product = models.ForeignKey(Product, on_delete=models.CASCADE, related_name='reviews')
    rating = models.FloatField(validators=[MinValueValidator(0), MaxValueValidator(5)], default=0)
    comment = models.TextField(blank=True, null=True)
    moderated = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
