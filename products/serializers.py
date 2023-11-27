from django.db.models import Q
from rest_framework import serializers

from service.serializers import ConversionField

from .models import Category, Product, ProductInventory, ProductReview, Tag


class CategorySerializer(serializers.ModelSerializer):
    class Meta:
        model = Category
        fields = ('id', 'name', 'level', 'parent_id')


class ShortProductSerializer(serializers.ModelSerializer):
    price = ConversionField(method_name='get_price')
    sale_price = ConversionField(method_name='get_sale_price')
    image = serializers.SerializerMethodField(read_only=True)

    class Meta:
        model = Product
        fields = ('id', 'name', 'price', 'sale_price', 'image', 'avg_rating',
                  'reviews_count', 'site_avg_rating', 'site_reviews_count')

    def get_price(self, instance):
        inventory = instance.inventories.first()
        if inventory:
            return inventory.price

    def get_sale_price(self, instance):
        inventory = instance.inventories.first()
        if inventory:
            return inventory.sale_price

    def get_image(self, instance):
        image = instance.images.first()
        if image:
            return image.url

    def update(self, instance, validated_data):
        raise NotImplementedError('`update()` not implemented.')

    def create(self, validated_data):
        raise NotImplementedError('`create()` not implemented.')


class ProductInventorySerializer(serializers.ModelSerializer):
    price = ConversionField()
    sale_price = ConversionField()

    class Meta:
        model = ProductInventory
        fields = ("id", 'item_code', 'name', 'can_choose_tags', "quantity", "status_code", 'price',
                  "sale_price", "color_image")


class ProductDetailSerializer(serializers.ModelSerializer):
    images = serializers.SlugRelatedField(many=True, read_only=True, slug_field='url')
    tags = serializers.SerializerMethodField(read_only=True)

    class Meta:
        model = Product
        fields = ('id', 'name',  'description',  'avg_rating', 'reviews_count',
                  'site_avg_rating', 'site_reviews_count', 'images', 'tags')

    def get_tags(self, instance):
        return Tag.collections.filter(
            Q(products__id=instance.id) | Q(product_inventories__product_id=instance.id)
        ).grouped_tags()


class ProductReviewSerializer(serializers.ModelSerializer):
    author_name = serializers.SlugRelatedField(slug_field="full_name", read_only=True, source='user')

    class Meta:
        model = ProductReview
        fields = ('id', 'author_name', 'product', 'rating', 'comment', 'created_at')
        extra_kwargs = {'product': {'write_only': True, 'required': True}}

    def validate(self, attrs):
        attrs['user'] = self.context['request'].user
        return attrs


class ProductReferenceSerializer(serializers.Serializer):
    exclude = serializers.PrimaryKeyRelatedField(
        queryset=Product.objects.all(),
        write_only=True,
        many=True,
        required=False
    )
