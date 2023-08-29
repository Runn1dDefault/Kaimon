from django.core.exceptions import ObjectDoesNotExist
from django.db.models import Q
from rest_framework import serializers

from users.serializers import UserProfileSerializer
from currency_conversion.mixins import CurrencySerializerMixin
from utils.mixins import LangSerializerMixin

from .models import Genre, Product, ProductDetail, GenreChild, ProductReview
from .utils import round_half_integer


class GenreChildSerializer(LangSerializerMixin, serializers.ModelSerializer):
    id = serializers.SerializerMethodField(read_only=True)
    name = serializers.SerializerMethodField(read_only=True)
    level = serializers.SerializerMethodField(read_only=True)

    class Meta:
        model = GenreChild
        fields = ('id', 'name', 'level')
        translate_fields = ('name',)

    def __init__(self, for_children: bool = False, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.for_children = for_children

    def get_fk_field(self, instance):
        if self.for_children:
            return instance.child
        return instance.parent

    def valid_translate_instance(self, instance):
        return self.get_fk_field(instance)

    def get_id(self, instance):
        return self.get_fk_field(instance).id

    def get_name(self, instance):
        return self.get_fk_field(instance).name

    def get_level(self, instance):
        return self.get_fk_field(instance).level


class GenreSerializer(LangSerializerMixin, serializers.ModelSerializer):
    children = serializers.SerializerMethodField(read_only=True)

    class Meta:
        model = Genre
        fields = ('id', 'name', 'level', 'children')
        translate_fields = ('name',)

    def get_children(self, instance):
        include_children = self.context.get('include_children', True)
        if include_children is False:
            return []

        all_children = instance.children.filter(
            Q(child__deactivated__isnull=True) | Q(child__deactivated=False)
        )

        next_level_children = all_children.filter(child__level=instance.level + 1)
        children = next_level_children
        if not next_level_children.exists():
            children = all_children
        return GenreChildSerializer(instance=children, many=True, for_children=True, context=self.context).data


class ProductDetailSerializer(LangSerializerMixin, serializers.ModelSerializer):
    class Meta:
        model = ProductDetail
        fields = ('id', 'name', 'value')
        translate_fields = ('name', 'value')


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


class ProductSerializer(CurrencySerializerMixin, LangSerializerMixin, serializers.ModelSerializer):
    reviews_count = serializers.SerializerMethodField(read_only=True)
    avg_rank = serializers.SerializerMethodField(read_only=True)
    discount_price = serializers.SerializerMethodField(read_only=True)

    class Meta:
        model = Product
        fields = ('id', 'name', 'price', 'discount_price', 'image_url', 'avg_rank', 'reviews_count', 'count')
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

    def get_discount_price(self, instance):
        if instance.price <= 0:
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


class ProductRetrieveSerializer(ProductSerializer):
    details = ProductDetailSerializer(many=True)

    class Meta:
        model = Product
        fields = ('id', 'name', 'description', 'price', 'discount_price', 'image_url', 'brand_name',
                  'avg_rank', 'reviews_count', 'count', 'details')
        translate_fields = ('name', 'description', 'brand_name',)
        currency_convert_fields = ('price',)
