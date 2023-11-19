from rest_framework import serializers

from currencies.serializers import ConversionField

from .models import Category, Product, ProductInventory, ProductReview


class CategorySerializer(serializers.ModelSerializer):
    class Meta:
        model = Category
        fields = ('id', 'name', 'level', 'parent')


class ShortProductSerializer(serializers.ModelSerializer):
    price = ConversionField()
    sale_price = ConversionField()
    images = serializers.SlugRelatedField(many=True, read_only=True, slug_field='url')

    class Meta:
        model = Product
        fields = ('id', 'name', 'price', 'sale_price', 'site_avg_rating', 'site_rating_count', 'images')

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
        fields = ('id', 'name',  'description', 'price', 'sale_price', 'site_avg_rating', 'site_rating_count',
                  'categories', 'images', 'inventories')

    def get_categories(self, instance):
        categories = instance.categories.filter(level__gt=0, deactivated=False).order_by('-level')
        return CategorySerializer(instance=categories, many=True, context=self.context).data


class ProductReviewSerializer(serializers.ModelSerializer):
    user = serializers.SlugRelatedField(slug_field="full_name", read_only=True)

    class Meta:
        model = ProductReview
        fields = ('id', 'user', 'product', 'rating', 'comment', 'created_at')
        extra_kwargs = {'product': {'write_only': True, 'required': True}}

    def validate(self, attrs):
        attrs['user'] = self.context['request'].user
        return attrs
