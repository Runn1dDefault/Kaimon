from django.contrib.auth import get_user_model
from django.core.exceptions import ObjectDoesNotExist
from django.core.validators import MaxValueValidator, MinValueValidator
from django.db import models

from language.models import LanguageModel
from utils.helpers import round_half_integer

from .querysets import GenreQuerySet, ProductQuerySet, TagGroupQuerySet, ReviewAnalyticsQuerySet
from .utils import increase_price


class Genre(models.Model):
    objects = GenreQuerySet.as_manager()

    id = models.BigIntegerField(primary_key=True)
    level = models.PositiveIntegerField(null=True, blank=True)
    deactivated = models.BooleanField(default=False, null=True)
    parent = models.ForeignKey('self', on_delete=models.SET_NULL, related_name='children', null=True)

    def __str__(self):
        return str(self.id)


class GenreTranslation(LanguageModel):
    genre = models.ForeignKey(Genre, on_delete=models.CASCADE, related_name='translations')
    name = models.CharField(max_length=100)


class TagGroup(models.Model):
    objects = TagGroupQuerySet.as_manager()
    id = models.BigIntegerField(primary_key=True)
    created_at = models.DateTimeField(auto_now_add=True)


class TagGroupTranslation(LanguageModel):
    group = models.ForeignKey(TagGroup, on_delete=models.CASCADE, related_name='translations')
    name = models.CharField(max_length=100)


class Tag(models.Model):
    objects = models.Manager()

    id = models.BigIntegerField(primary_key=True)
    created_at = models.DateTimeField(auto_now_add=True)
    group = models.ForeignKey(TagGroup, on_delete=models.CASCADE, related_name='tags', null=True, blank=True)


class TagTranslation(LanguageModel):
    tag = models.ForeignKey(Tag, on_delete=models.CASCADE, related_name='translations')
    name = models.CharField(max_length=100)


class Product(models.Model):
    objects = ProductQuerySet.as_manager()

    id = models.CharField(max_length=255, primary_key=True)
    rakuten_price = models.DecimalField(max_digits=20, decimal_places=10, null=True)
    price = models.DecimalField(max_digits=20, decimal_places=10, null=True)

    product_url = models.TextField(blank=True, null=True)
    availability = models.BooleanField(default=True)

    created_at = models.DateTimeField(auto_now_add=True)
    modified_at = models.DateTimeField(auto_now=True)

    is_active = models.BooleanField(default=True)
    reference_rank = models.IntegerField(null=True, blank=True)

    @property
    def reviews_count(self) -> int:
        reviews = getattr(self, 'reviews')
        return reviews.filter(is_active=True).count()

    @property
    def sale_price(self) -> float | None:
        if not self.price:
            self.price = increase_price(self.rakuten_price)
            self.save()

        if not self.availability or not self.price or self.price <= 0:
            return None

        promotions = getattr(self, 'promotions')
        promotion = promotions.active_promotions().first()
        if not promotion:
            return None

        try:
            discount = promotion.discount
        except ObjectDoesNotExist:
            # in the future here can be changed, when new promotion logic will be added
            return None

        return discount.calc_price(self.price)

    @property
    def avg_rank(self):
        reviews = getattr(self, 'reviews')
        reviews = reviews.filter(is_active=True)
        if reviews.exists():
            return sum(reviews.values_list('rank', flat=True)) / reviews.count()
        return 0.0


class ProductTranslation(LanguageModel):
    product = models.ForeignKey(Product, on_delete=models.CASCADE, related_name='translations')
    name = models.CharField(max_length=255)
    description = models.TextField(blank=True, null=True)


class ProductGenre(models.Model):
    objects = models.Manager()

    product = models.ForeignKey(Product, on_delete=models.CASCADE, related_name='genres')
    genre = models.ForeignKey(Genre, on_delete=models.CASCADE)


class ProductTag(models.Model):
    objects = models.Manager()

    product = models.ForeignKey(Product, on_delete=models.CASCADE, related_name='tags')
    tag = models.ForeignKey(Tag, on_delete=models.CASCADE)


class ProductImageUrl(models.Model):
    objects = models.Manager()

    product = models.ForeignKey(Product, on_delete=models.CASCADE, related_name='images')
    url = models.TextField()


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
