from rest_framework import serializers

from currencies.serializers import ConversionField
from users.serializers import UserProfileSerializer
from utils.serializers.mixins import LangSerializerMixin

from .models import Genre, Product, ProductReview, TagGroup, Tag


class GenreSerializer(LangSerializerMixin, serializers.ModelSerializer):
    class Meta:
        model = Genre
        fields = ('id', 'name', 'level')
        translate_fields = ('name',)


class ProductReviewSerializer(LangSerializerMixin, serializers.ModelSerializer):
    user = UserProfileSerializer(hide_fields=['role', 'email'], read_only=True)
    product_name = serializers.SerializerMethodField(read_only=True)  # TODO: delete this field if not used on front

    class Meta:
        model = ProductReview
        fields = ('id', 'user', 'product', 'product_name', 'rank', 'comment', 'created_at')
        extra_kwargs = {'product': {'write_only': True, 'required': True}}

    def validate(self, attrs):
        user = self.context['request'].user
        assert user.is_authenticated, f'Serializer {self.__class__.__name__} not available to {user.__class__.__name__}'
        attrs['user'] = user
        return attrs

    def get_product_name(self, instance):
        product = instance.product
        translate_field = self.get_translate_field('name')
        return getattr(product, translate_field, None) or product.name


class ProductListSerializer(LangSerializerMixin, serializers.ModelSerializer):
    price = ConversionField()
    sale_price = ConversionField()
    image_urls = serializers.SlugRelatedField(many=True, read_only=True, slug_field='url')

    class Meta:
        model = Product
        fields = ('id', 'name', 'price', 'sale_price', 'availability', 'avg_rank', 'reviews_count', 'image_urls',
                  'created_at', 'genre_id')
        translate_fields = ('name',)

    def __init__(self, instance=None, **kwargs):
        kwargs['many'] = True
        super().__init__(instance=instance, data=None, **kwargs)


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


class ProductRetrieveSerializer(LangSerializerMixin, serializers.ModelSerializer):
    price = ConversionField()
    sale_price = ConversionField()
    image_urls = serializers.SlugRelatedField(many=True, read_only=True, slug_field='url')
    tags_info = serializers.SerializerMethodField(read_only=True)

    class Meta:
        model = Product
        fields = ('id', 'name', 'price', 'sale_price', 'availability', 'avg_rank', 'reviews_count', 'image_urls',
                  'created_at', 'genre_id', 'description', 'tags_info')
        translate_fields = ('name', 'description')
        currency_convert_fields = ('sale_price', 'price',)

    def __init__(self, instance, **kwargs):
        assert isinstance(instance, Product)
        kwargs['many'] = False
        super().__init__(instance=instance, data=None, **kwargs)

    def get_tags_info(self, instance):
        tags_queryset = Tag.objects.filter(producttag__product_id=instance.id)
        if not tags_queryset.exists():
            return
        group_ids = tags_queryset.order_by('group_id').distinct('group_id').values_list('group_id', flat=True)
        groups_queryset = TagGroup.objects.filter(id__in=group_ids)
        return TagByGroupSerializer(
            tag_ids=tags_queryset.values_list('id', flat=True),
            instance=groups_queryset,
            many=True,
            context=self.context
        ).data
