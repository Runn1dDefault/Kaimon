from django.core.exceptions import ObjectDoesNotExist
from rest_framework import serializers

from currencies.mixins import CurrencySerializerMixin
from users.serializers import UserProfileSerializer
from utils.mixins import LangSerializerMixin

from .models import Genre, Product, ProductReview
from .utils import round_half_integer


class GenreSerializer(LangSerializerMixin, serializers.ModelSerializer):
    class Meta:
        model = Genre
        fields = ('id', 'name', 'level')
        translate_fields = ('name',)


class ProductReviewSerializer(LangSerializerMixin, serializers.ModelSerializer):
    user = UserProfileSerializer(hide_fields=['role', 'email'], read_only=True)
    product_name = serializers.SerializerMethodField(read_only=True)

    class Meta:
        model = ProductReview
        fields = ('id', 'user', 'product', 'product_name', 'rank', 'comment')
        extra_kwargs = {'product': {'write_only': True, 'required': True}}

    def validate(self, attrs):
        attrs['user'] = self.context['request'].user
        rank = attrs.get('rank')
        if rank:
            attrs['rank'] = round_half_integer(rank)
        return attrs

    def get_product_name(self, instance):
        product = instance.product
        translate_field = self.get_translate_field('name')
        return getattr(product, translate_field, None) or product.name


class ProductListSerializer(CurrencySerializerMixin, LangSerializerMixin, serializers.ModelSerializer):
    avg_rank = serializers.SerializerMethodField(read_only=True)
    reviews_count = serializers.SerializerMethodField(read_only=True)
    sale_price = serializers.SerializerMethodField(read_only=True)
    image_urls = serializers.SlugRelatedField(many=True, read_only=True, slug_field='url')

    class Meta:
        model = Product
        fields = ('id', 'name', 'price', 'sale_price', 'availability', 'avg_rank', 'reviews_count', 'image_urls',
                  'created_at')
        translate_fields = ('name',)
        currency_convert_fields = ('price',)

    def get_avg_rank(self, instance):
        reviews = instance.reviews.filter(is_active=True)
        if reviews.exists():
            ranks = list(reviews.values_list('rank', flat=True))
            return sum(ranks) / len(ranks)
        return 0

    def get_reviews_count(self, instance):
        return instance.reviews.filter(is_active=True).count()

    def get_sale_price(self, instance):
        if not instance.availability or instance.price <= 0:
            return None

        promotion = instance.promotions.active_promotions().first()
        if not promotion:
            return None

        try:
            discount = promotion.discount
        except ObjectDoesNotExist:
            # in the future here can be changed, when new promotion logic will be added
            return None

        discount_price = discount.calc_price(instance.price)
        if self.get_currency() == 'yen':
            return discount_price
        return self.get_converted_price(discount_price)


class ProductRetrieveSerializer(ProductListSerializer):
    def __init__(self, *args, **kwargs):
        kwargs['many'] = False
        super().__init__(*args, **kwargs)

    class Meta(ProductListSerializer.Meta):
        model = Product
        fields = ('id', 'name', 'price', 'description', 'sale_price', 'availability', 'avg_rank', 'reviews_count',
                  'image_urls')
        translate_fields = ('name', 'description',)

