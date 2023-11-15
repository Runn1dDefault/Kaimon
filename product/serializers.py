from rest_framework import serializers

from currencies.serializers import ConversionField
from users.serializers import UserProfileSerializer

from .models import Genre, Product, ProductReview


class GenreSerializer(serializers.ModelSerializer):
    class Meta:
        model = Genre
        fields = ('id', 'name', 'level')


class ProductReviewSerializer(serializers.ModelSerializer):
    user = UserProfileSerializer(hide_fields=('role', 'email', 'email_confirmed', 'registration_payed'), read_only=True)

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
    price = ConversionField()
    sale_price = ConversionField()
    image_urls = serializers.SlugRelatedField(many=True, read_only=True, slug_field='url')

    class Meta:
        model = Product
        fields = ('id', 'name', 'price', 'sale_price', 'availability', 'avg_rank', 'reviews_count', 'image_urls')

    def __init__(self, instance=None, **kwargs):
        kwargs['many'] = True
        super().__init__(instance=instance, data=None, **kwargs)

    def update(self, instance, validated_data):
        raise NotImplementedError('`update()` not implemented.')

    def create(self, validated_data):
        raise NotImplementedError('`create()` not implemented.')


class ProductRetrieveSerializer(serializers.ModelSerializer):
    price = ConversionField()
    sale_price = ConversionField()
    image_urls = serializers.SlugRelatedField(many=True, read_only=True, slug_field='url')
    genres = serializers.SerializerMethodField(read_only=True)

    class Meta:
        model = Product
        fields = ('id', 'name', 'price', 'sale_price', 'availability', 'avg_rank', 'reviews_count', 'description',
                  'genres', 'image_urls')

    def get_genres(self, instance):
        genres = instance.genres.filter(level__gt=0, deactivated=False)
        return GenreSerializer(instance=genres, many=True, context=self.context).data
