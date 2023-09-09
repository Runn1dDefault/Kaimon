from rest_framework import serializers

from currencies.mixins import CurrencySerializerMixin
from users.serializers import UserProfileSerializer
from utils.mixins import LangSerializerMixin
from utils.helpers import round_half_integer

from .models import Genre, Product, ProductReview, TagGroup, Tag
from .utils import get_product_avg_rank


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
        fields = ('id', 'user', 'product', 'product_name', 'rank', 'comment', 'created_at')
        extra_kwargs = {'product': {'write_only': True, 'required': True}}

    def validate(self, attrs):
        attrs['user'] = self.context['request'].user
        return attrs

    def get_product_name(self, instance):
        product = instance.product
        translate_field = self.get_translate_field('name')
        return getattr(product, translate_field, None) or product.name


class ProductListSerializer(CurrencySerializerMixin, LangSerializerMixin, serializers.ModelSerializer):
    sale_price = serializers.SerializerMethodField(read_only=True)
    avg_rank = serializers.SerializerMethodField(read_only=True)
    image_urls = serializers.SlugRelatedField(many=True, read_only=True, slug_field='url')

    class Meta:
        model = Product
        fields = ('id', 'name', 'price', 'sale_price', 'availability', 'avg_rank', 'reviews_count', 'image_urls',
                  'created_at', 'genre_id')
        translate_fields = ('name',)
        currency_convert_fields = ('price',)

    def get_avg_rank(self, instance):
        return get_product_avg_rank(instance)

    def get_sale_price(self, instance):
        currency = self.get_currency()
        if currency == 'yen':
            return instance.sale_price
        if instance.sale_price:
            return self.get_converted_price(instance.sale_price, currency)


class TagSerializer(LangSerializerMixin, serializers.ModelSerializer):
    class Meta:
        model = Tag
        fields = ('id', 'name')
        translate_fields = ('name',)


class TagByGroupSerializer(LangSerializerMixin, serializers.ModelSerializer):
    tags = serializers.SerializerMethodField(read_only=True)

    def __init__(self, instance=None, data=None, tag_ids: list[int] = None, **kwargs):
        super().__init__(instance=instance, data=data, **kwargs)
        self.tag_ids = tag_ids

    class Meta:
        model = TagGroup
        fields = ('id', 'name', 'tags')
        translate_fields = ('name',)

    def get_tags(self, instance):
        if self.tag_ids:
            queryset = instance.tags.filter(id__in=self.tag_ids)
        else:
            queryset = instance.tags.all()
        return TagSerializer(instance=queryset, many=True, context=self.context).data


class ProductRetrieveSerializer(ProductListSerializer):
    tags_info = serializers.SerializerMethodField(read_only=True)

    def __init__(self, *args, **kwargs):
        kwargs['many'] = False
        super().__init__(*args, **kwargs)

    class Meta(ProductListSerializer.Meta):
        fields = (*ProductListSerializer.Meta.fields,  'description', 'tags_info')
        translate_fields = (*ProductListSerializer.Meta.translate_fields, 'description')

    def get_tags_info(self, instance):
        if not instance.tags.exists():
            return
        group_ids = list(instance.tags.all().order_by('group_id')
                                            .distinct('group_id')
                                            .values_list('group_id', flat=True))
        tag_ids = list(instance.tags.values_list('id', flat=True))
        groups_queryset = TagGroup.objects.filter(id__in=group_ids)
        return TagByGroupSerializer(tag_ids=tag_ids, instance=groups_queryset, many=True, context=self.context).data
