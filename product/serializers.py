from rest_framework import serializers
from rest_framework.fields import empty

from currencies.serializers import ConversionField
from users.serializers import UserProfileSerializer
from utils.serializers.mixins import LangSerializerMixin

from .models import Genre, Product, ProductReview, TagGroup, Tag


class GenreSerializer(LangSerializerMixin, serializers.ModelSerializer):
    class Meta:
        model = Genre
        fields = ('id', 'name', 'level')
        translate_fields = ('name',)


class ProductReviewSerializer(serializers.ModelSerializer):
    user = UserProfileSerializer(hide_fields=('role', 'email'), read_only=True)

    class Meta:
        model = ProductReview
        fields = ('id', 'user', 'product', 'rank', 'comment', 'created_at')
        extra_kwargs = {'product': {'write_only': True, 'required': True}}

    def validate(self, attrs):
        user = self.context['request'].user
        assert user.is_authenticated, f'Serializer {self.__class__.__name__} not available to {user.__class__.__name__}'
        attrs['user'] = user
        return attrs


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

    def update(self, instance, validated_data):
        raise NotImplementedError('`update()` not implemented.')

    def create(self, validated_data):
        raise NotImplementedError('`create()` not implemented.')


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

    def __init__(self, instance, **kwargs):
        assert isinstance(instance, Product)
        kwargs['many'] = False
        super().__init__(instance=instance, data=empty, **kwargs)

    def get_tags_info(self, instance):
        tags_fk = instance.tags.all()
        if not tags_fk.exists():
            return []

        group_ids = tags_fk.order_by('tag__group_id').distinct('tag__group_id').values_list('tag__group_id', flat=True)
        groups_queryset = TagGroup.objects.filter(id__in=group_ids)
        tag_translate_field = self.get_translate_field('name')
        return groups_queryset.tags_list(
            name_field=tag_translate_field,
            tag_ids=tags_fk.values_list('tag_id', flat=True)
        )
