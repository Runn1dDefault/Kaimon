import json

from django.core.files.storage import default_storage
from rest_framework import serializers

from service.models import Currencies
from service.serializers import ConversionField
from service.utils import get_currency_by_id, get_currencies_price_per, convert_price, increase_price

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
        prices_template = {"price": 0.0, "sale_price": 0.0}
        if isinstance(instance, dict):
            inventory_info = instance.get("inventory_info", {})
            if isinstance(inventory_info, str):
                inventory_info = json.loads(inventory_info)

            if not inventory_info:
                return prices_template

            obj_id = instance.get('id')
            site_price = inventory_info.get("site_price") or 0.0
            increase_per = inventory_info.get("increase_per") or 0.0
            sale_price = inventory_info.get("sale_price")
        else:
            inventory = instance.inventories.first()
            if not inventory:
                return prices_template

            obj_id = instance.id
            site_price = inventory.site_price
            increase_per = inventory.increase_per
            sale_price = inventory.sale_price

        price = site_price if increase_per <= 0 else increase_price(site_price, increase_per)
        currency = self.context['currency']
        obj_currency = get_currency_by_id(obj_id)
        if currency == obj_currency:
            prices_template['price'] = price
            prices_template['sale_price'] = sale_price
            return prices_template

        if currency != Currencies.moneta:
            price_per = get_currencies_price_per(currency_from=obj_currency, currency_to=currency)
            prices_template['price'] = convert_price(price, price_per) if price_per else 0.0
            prices_template['sale_price'] = convert_price(sale_price, price_per) if sale_price and price_per else None
            return prices_template

        if obj_currency == Currencies.usd:
            price_per = get_currencies_price_per(currency_from=Currencies.moneta, currency_to=Currencies.usd)
            prices_template['price'] = convert_price(price, price_per, divide=True) if price_per else 0.0
            prices_template['sale_price'] = (
                convert_price(sale_price, price_per, divide=True) if sale_price and price_per else None
            )
            return prices_template

        usd_price_per = get_currencies_price_per(currency_from=obj_currency, currency_to=Currencies.usd)
        if not usd_price_per:
            return prices_template

        moneta_price_per = get_currencies_price_per(currency_from=Currencies.moneta, currency_to=Currencies.usd)
        if not moneta_price_per:
            return prices_template

        usd_price = convert_price(price, usd_price_per)
        usd_sale = convert_price(sale_price, usd_price_per)
        prices_template["price"] = convert_price(usd_price, moneta_price_per, divide=True)
        prices_template['sale_price'] = convert_price(usd_sale, moneta_price_per, divide=True)
        return prices_template

    def get_image(self, instance):
        if isinstance(instance, dict):
            image_info = instance.get('image_info')
            if not image_info:
                return

            if isinstance(image_info, str):
                image_info = json.loads(image_info)

            image = image_info.get("image")
            if image:
                image = default_storage.url(image)
                request = self.context['request']
                return request.build_absolute_uri(image)

            return image_info.get("url") or None

        image_obj = instance.images.only("url", "image").first()
        if not image_obj:
            return

        if image_obj.image:
            request = self.context['request']
            return request.build_absolute_uri(image_obj.image)
        return image_obj.url or None


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
