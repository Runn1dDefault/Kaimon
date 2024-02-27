from django.core.files.storage import default_storage
from rest_framework import serializers

from service.serializers import ConversionField
from service.utils import get_currency_by_id, get_currencies_price_per, convert_price, increase_price, check_to_json

from .models import Category, Product, ProductInventory, ProductReview, ProductImage


class CategorySerializer(serializers.ModelSerializer):
    class Meta:
        model = Category
        fields = ('id', 'name', 'level', 'parent_id')


class ShortProductSerializer(serializers.ModelSerializer):
    prices = serializers.SerializerMethodField(read_only=True)
    image = serializers.SerializerMethodField(read_only=True)

    class Meta:
        model = Product
        fields = ('id', 'name', 'avg_rating', 'reviews_count', 'prices', "image")

    def get_prices(self, instance):
        if isinstance(instance, dict):
            obj_id = instance.get('id')
            inventory = check_to_json(instance, "inventory_info")
        else:
            obj_id = instance.id
            inventory = instance.inventories.first()

        if not inventory:
            return {"price": 0.0, "sale_price": 0.0}

        if isinstance(inventory, dict):
            site_price = inventory.get("site_price") or 0.0
            increase_per = inventory.get("increase_per") or 0.0
            sale_price = inventory.get("sale_price")
        else:
            site_price = inventory.site_price
            increase_per = inventory.increase_per
            sale_price = inventory.sale_price

        price = site_price if increase_per <= 0 else increase_price(site_price, increase_per)
        obj_currency = get_currency_by_id(obj_id)
        currency = self.context.get('currency', obj_currency)

        if obj_currency != currency:
            price_per = get_currencies_price_per(currency_from=obj_currency, currency_to=currency)
            price = convert_price(price, price_per) if price_per else 0.0
            sale_price = convert_price(sale_price, price_per) if sale_price and price_per else None

        return {"price": price, "sale_price": sale_price}

    def get_image(self, instance):
        request = self.context['request']
        if isinstance(instance, dict):
            image_obj = check_to_json(instance, "image_info") or {}
        else:
            image = instance.images.only("url", "image").first()
            image_obj = {"image": image.image, "url": image.url} if image else {}

        filepath = image_obj.get("image")
        if filepath:
            return request.build_absolute_uri(default_storage.url(filepath))
        return image_obj.get('url') or None


class ProductInventorySerializer(serializers.ModelSerializer):
    price = ConversionField()
    sale_price = ConversionField()
    size = serializers.SerializerMethodField(read_only=True)
    color = serializers.SerializerMethodField(read_only=True)
    color_name = serializers.SerializerMethodField(read_only=True)
    size_name = serializers.SerializerMethodField(read_only=True)

    def __init__(self, *args, **kwargs):
        self._include_products = kwargs.pop("include_products", False)
        super().__init__(*args, **kwargs)

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

    def to_representation(self, instance):
        data = super().to_representation(instance)
        if self._include_products:
            request = self.context["request"]

            image = instance.product.images.first()
            image_url = None
            if image:
                image_url = request.build_absolute_uri(image.image.url) if image.image else image.url

            data["product"] = {
                "id": instance.product.id,
                "name": instance.product.name,
                "image": image_url
            }
        return data


class ProductImageSerializer(serializers.ModelSerializer):
    class Meta:
        model = ProductImage
        fields = ('image', 'url')


class ProductDetailSerializer(serializers.ModelSerializer):
    images = ProductImageSerializer(many=True, read_only=True)
    inventories = ProductInventorySerializer(many=True, read_only=True)

    class Meta:
        model = Product
        fields = ('id', 'name',  'description',  'avg_rating', 'reviews_count', 'can_choose_tags',
                  'images', 'inventories')


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
