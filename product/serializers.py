from typing import Iterable

from rest_framework import serializers

from currencies.serializers import ConversionField
from language.serializers import TranslateField
from users.serializers import UserProfileSerializer
from .helpers import grouped_tags

from .models import Genre, Product, ProductReview, TagGroup, Tag


class GenreSerializer(serializers.ModelSerializer):
    name = TranslateField(read_only=True)

    class Meta:
        model = Genre
        fields = ('id', 'name', 'level')


class ProductReviewSerializer(serializers.ModelSerializer):
    user = UserProfileSerializer(
        hide_fields=('role', 'email', 'email_confirmed', 'registration_payed'),
        read_only=True
    )

    class Meta:
        model = ProductReview
        fields = ('id', 'user', 'product', 'rank', 'comment', 'created_at')
        extra_kwargs = {'product': {'write_only': True, 'required': True}}

    def validate(self, attrs):
        user = self.context['request'].user
        assert user.is_authenticated, f'Serializer {self.__class__.__name__} not available to {user.__class__.__name__}'
        attrs['user'] = user
        return attrs


class ProductIdsSerializer(serializers.Serializer):
    product_ids = serializers.PrimaryKeyRelatedField(
        queryset=Product.objects.filter(is_active=True),
        required=True,
        many=True
    )


class ProductListSerializer(serializers.ModelSerializer):
    name = TranslateField(read_only=True)
    description = TranslateField(read_only=True)

    price = ConversionField()
    sale_price = ConversionField()
    image_urls = serializers.SlugRelatedField(many=True, read_only=True, slug_field='url')

    class Meta:
        model = Product
        fields = ('id', 'name', 'description', 'price', 'sale_price', 'availability', 'avg_rank', 'reviews_count',
                  'image_urls')

    def __init__(self, instance=None, **kwargs):
        kwargs['many'] = True
        kwargs['read_only'] = True
        super().__init__(instance=instance, data=None, **kwargs)


class TagSerializer(serializers.ModelSerializer):
    name = TranslateField(read_only=True)

    class Meta:
        model = Tag
        fields = ('id', 'name')


class TagGroupSerializer(serializers.ModelSerializer):
    name = TranslateField(read_only=True)
    tags = serializers.SerializerMethodField(read_only=True)

    class Meta:
        model = TagGroup
        fields = ('id', 'name', 'tags')

    def __init__(self, instance=None, data=None, tag_ids: Iterable[int] = None, **kwargs):
        self.tag_ids = tag_ids
        super().__init__(instance=instance, data=data, **kwargs)

    def get_tags(self, instance):
        if not instance.tags.exists():
            return []

        queryset = instance.tags.all()
        if self.tag_ids:
            queryset = queryset.filter(id__in=self.tag_ids)

        return TagSerializer(instance=queryset, many=True, context=self.context).data


class ProductRetrieveSerializer(serializers.ModelSerializer):
    name = TranslateField(read_only=True)
    description = TranslateField(read_only=True)
    price = ConversionField()
    sale_price = ConversionField()

    images = serializers.SlugRelatedField(slug_field='url', read_only=True, many=True)
    genres = serializers.SerializerMethodField(read_only=True)
    tag_groups = serializers.SerializerMethodField(read_only=True)

    class Meta:
        model = Product
        fields = ('id', 'name', 'description', 'price', 'sale_price', 'availability', 'avg_rank',
                  'reviews_count', 'genres', 'images', 'tag_groups')

    def get_genres(self, instance):
        genres_fk = instance.genres.filter(genre__deactivated=False)
        if not genres_fk.exists():
            return []

        genres = (
            Genre.objects.exclude(level=0)
            .filter(id__in=genres_fk.values_list('genre_id', flat=True))
            .order_by('-level')
        )
        return GenreSerializer(instance=genres, many=True, context=self.context).data

    def get_tag_groups(self, instance):
        if not instance.tags.exists():
            return []

        tags_queryset = instance.tags.all()
        group_ids = (
            tags_queryset.order_by('tag__group_id')
            .distinct('tag__group_id')
            .values_list('tag__group_id', flat=True)
        )
        return grouped_tags(
            group_queryset=TagGroup.objects.filter(id__in=group_ids),
            lang=self.context.get('lang', 'ja'),
            tag_ids=tags_queryset.values_list('tag_id', flat=True)
        )
