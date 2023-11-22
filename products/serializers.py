from rest_framework import serializers

from service.serializers import ConversionField

from .models import Category, Product, ProductInventory, ProductReview


class CategorySerializer(serializers.ModelSerializer):
    class Meta:
        model = Category
        fields = ('id', 'name', 'level', 'parent_id')


class ShortProductSerializer(serializers.ModelSerializer):
    price = ConversionField()
    sale_price = ConversionField()
    image = serializers.SerializerMethodField(read_only=True)

    class Meta:
        model = Product
        fields = ('id', 'name', 'price', 'sale_price', 'image', 'avg_rating',
                  'reviews_count', 'site_avg_rating', 'site_reviews_count')

    def get_image(self, instance):
        image = instance.images.first()
        if image:
            return image.url

    def update(self, instance, validated_data):
        raise NotImplementedError('`update()` not implemented.')

    def create(self, validated_data):
        raise NotImplementedError('`create()` not implemented.')


class ProductInventorySerializer(serializers.ModelSerializer):
    class Meta:
        model = ProductInventory
        fields = ("price", "quantity", "color", "color_image_url", "size", "status_code")


class ProductDetailSerializer(serializers.ModelSerializer):
    price = ConversionField()
    sale_price = ConversionField()
    images = serializers.SlugRelatedField(many=True, read_only=True, slug_field='url')
    categories = serializers.SerializerMethodField(read_only=True)
    inventories = ProductInventorySerializer(many=True, read_only=True)

    class Meta:
        model = Product
        fields = ('id', 'name',  'description', 'price', 'sale_price', 'avg_rating', 'reviews_count',
                  'site_avg_rating', 'site_reviews_count', 'categories', 'images', 'inventories')

    def get_categories(self, instance):
        categories = instance.categories.filter(level__gt=0, deactivated=False).order_by('-level')
        return CategorySerializer(instance=categories, many=True, context=self.context).data


class ProductReviewSerializer(serializers.ModelSerializer):
    author_name = serializers.SlugRelatedField(slug_field="full_name", read_only=True, source='user')

    class Meta:
        model = ProductReview
        fields = ('id', 'author_name', 'product', 'rating', 'comment', 'created_at')
        extra_kwargs = {'product': {'write_only': True, 'required': True}}

    def validate(self, attrs):
        attrs['user'] = self.context['request'].user
        return attrs
