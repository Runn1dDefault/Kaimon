from django.db.models import Q
from rest_framework import serializers

from service.serializers import ConversionField
from service.utils import get_currency_by_id, get_currencies_price_per, convert_price

from .models import Category, Product, ProductInventory, ProductReview, Tag


class CategorySerializer(serializers.ModelSerializer):
    class Meta:
        model = Category
        fields = ('id', 'name', 'level', 'parent_id')


class ShortProductSerializer(serializers.ModelSerializer):
    prices = serializers.SerializerMethodField(read_only=True)
    image = serializers.SerializerMethodField(read_only=True)

    class Meta:
        model = Product
        fields = ('id', 'name', 'prices', 'image', 'avg_rating', 'reviews_count')

    def get_prices(self, instance):
        inventory = instance.inventories.only("sale_price", "site_price", "increase_per").first()
        if not inventory:
            return

        inst_currency = get_currency_by_id(instance.id)
        currency = self.context['currency']
        if currency != inst_currency:
            price_per = get_currencies_price_per(currency_from=inst_currency, currency_to=currency)
            return {
                "price": convert_price(inventory.price, price_per) if price_per else None,
                "sale_price": convert_price(inventory.sale_price, price_per)
                if price_per and inventory.sale_price else None
            }
        return {
            "price": inventory.price,
            "sale_price": inventory.sale_price,
        }

    def get_image(self, instance):
        obj = instance.images.only("image", "url").first()
        if obj:
            request = self.context['request']
            return request.build_absolute_uri(obj.image.url) if obj.image else obj.url


class ProductInventorySerializer(serializers.ModelSerializer):
    price = ConversionField()
    sale_price = ConversionField()
    size = serializers.SerializerMethodField(read_only=True)
    color = serializers.SerializerMethodField(read_only=True)
    color_name = serializers.SerializerMethodField(read_only=True)
    size_name = serializers.SerializerMethodField(read_only=True)

    class Meta:
        model = ProductInventory
        fields = ("id", 'item_code', 'name', "quantity", "status_code", 'price',
                  "sale_price", "color_image", 'size', 'color', 'color_name', 'size_name')

    def get_size(self, instance):
        if 'uniqlo' not in instance.id:
            return

        size = instance.tags.filter(group_id="uniqlo_s1izes").only("id").first()
        if size:
            return size.id

    def get_size_name(self, instance):
        if 'uniqlo' not in instance.id:
            return

        size = instance.tags.filter(group_id="uniqlo_s1izes").only("name").first()
        if size:
            return size.name

    def get_color_name(self, instance):
        if 'uniqlo' not in instance.id:
            return

        color = instance.tags.filter(group_id="uniqlo_c1olors").only("name").first()
        if color:
            return color.name

    def get_color(self, instance):
        if 'uniqlo' not in instance.id:
            return

        color = instance.tags.filter(group_id="uniqlo_c1olors").only("id").first()
        if color:
            return color.id


class ProductDetailSerializer(serializers.ModelSerializer):
    images = serializers.SerializerMethodField(read_only=True)
    tags = serializers.SerializerMethodField(read_only=True)
    inventories = ProductInventorySerializer(many=True, read_only=True)

    class Meta:
        model = Product
        fields = ('id', 'name',  'description',  'avg_rating', 'reviews_count', 'can_choose_tags',
                  'images', 'inventories', 'tags')

    def get_tags(self, instance):
        return Tag.collections.filter(
            Q(products__id=instance.id) | Q(product_inventories__product_id=instance.id)
        ).grouped_tags()

    def get_images(self, instance) -> list[str]:
        request = self.context['request']
        return [
            request.build_absolute_uri(obj.image.url) if obj.image else obj.url
            for obj in instance.images.all().only("url", "image")
        ]


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
