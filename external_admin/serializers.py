from typing import Any

from django.conf import settings
from django.core.exceptions import ObjectDoesNotExist
from django.core.validators import MaxValueValidator
from django.utils.translation import gettext_lazy as _
from rest_framework import serializers

from orders.serializers import OrderConversionField
from orders.utils import order_currencies_price_per
from products.models import Product, Category, Tag, ProductImage, ProductReview, ProductInventory
from products.serializers import ShortProductSerializer
from promotions.models import Banner, Promotion, Discount
from orders.models import Order, Customer, DeliveryAddress, Receipt, OrderShipping, OrderConversion, Payment
from service.models import Conversion, Currencies
from service.serializers import ConversionField, AnalyticsSerializer
from service.utils import get_currencies_price_per, recursive_single_tree, get_currency_by_id, uid_generate, \
    convert_price
from users.models import User


class UserAdminSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ('id', 'email', 'full_name', 'role', 'is_active', 'date_joined', 'last_login', 'registration_payed')
        extra_kwargs = {'role': {'read_only': True}}


class ConversionAdminSerializer(serializers.ModelSerializer):
    class Meta:
        model = Conversion
        fields = ('id', 'currency_from', 'currency_to', 'price_per')
        extra_kwargs = {'currency_from': {'read_only': True}, 'currency_to': {'read_only': True}}

    def save(self, **kwargs):
        instance = super().save(**kwargs)
        get_currencies_price_per.cache_clear()
        return instance


class TagAdminSerializer(serializers.ModelSerializer):
    group = serializers.SlugRelatedField(slug_field="name", read_only=True)
    group_id = serializers.PrimaryKeyRelatedField(
        queryset=Tag.objects.filter(group__isnull=True),
        write_only=True,
        required=False
    )

    class Meta:
        model = Tag
        fields = ('id', 'name', "group", "group_id")


class ProductImageLoaderSerializer(serializers.Serializer):
    images = serializers.ListField(child=serializers.ImageField(), write_only=True, required=True)


class ProductImageAdminSerializer(serializers.ModelSerializer):
    product = serializers.PrimaryKeyRelatedField(queryset=Product.objects.all(), write_only=True, required=True)
    url = serializers.URLField(required=False)

    class Meta:
        model = ProductImage
        fields = ('id', 'product', 'url', 'image')


class CategoryAdminSerializer(serializers.ModelSerializer):
    class Meta:
        model = Category
        fields = '__all__'


class ShortProductAdminSerializer(ShortProductSerializer):
    class Meta:
        model = Product
        fields = ('id', 'name', 'avg_rating', 'reviews_count', 'prices', "image", "is_active")


class ProductInventorySerializer(serializers.ModelSerializer):
    product = serializers.PrimaryKeyRelatedField(queryset=Product.objects.all(), required=True)
    site_price = ConversionField(all_conversions=True)
    sale_price = ConversionField(all_conversions=True, read_only=True)
    tag_ids = serializers.PrimaryKeyRelatedField(
        queryset=Tag.objects.filter(group__isnull=False),
        many=True,
        write_only=True,
        required=False
    )
    tags = serializers.SerializerMethodField(read_only=True)

    class Meta:
        model = ProductInventory
        fields = ("id", "product", "item_code", "site_price", "product_url", "name", "tags",
                  "quantity", "status_code", "increase_per", "sale_price", "color_image", "tag_ids")
        extra_kwargs = {
            "id": {"read_only": True},
            "name": {"required": True},
            "item_code": {"read_only": True},
            "product_url": {'read_only': True},
            "color_image": {"read_only": True},
        }

    def get_tags(self, instance):
        return Tag.collections.filter(id__in=instance.tags.all()).grouped_tags()

    def create(self, validated_data):
        product = validated_data['product']
        validated_data['id'] = uid_generate()
        validated_data['item_code'] = product.id
        validated_data['product_url'] = settings.PRODUCT_URL_TEMPLATE.format(product_id=product.id)
        tags = validated_data.pop('tag_ids', None)
        instance = super().create(validated_data)
        instance.tags.add(*tags)
        return instance

    def update(self, instance, validated_data):
        tags = validated_data.pop('tag_ids', None)
        if tags:
            instance.tags.clear()
            instance.tags.add(*tags)
        return super().update(instance, validated_data)


class ProductDetailAdminSerializer(serializers.ModelSerializer):
    categories = CategoryAdminSerializer(many=True, read_only=True)
    category = serializers.PrimaryKeyRelatedField(
        queryset=Category.objects.exclude(level=0),
        many=False,
        write_only=True,
        required=True
    )
    tags = serializers.PrimaryKeyRelatedField(
        queryset=Tag.objects.filter(group__isnull=False),
        many=True,
        write_only=True,
        required=False
    )
    images = ProductImageAdminSerializer(many=True, read_only=True)
    set_images = serializers.ListField(child=serializers.ImageField(), write_only=True, required=True)
    discount = serializers.SerializerMethodField(read_only=True)

    class Meta:
        model = Product
        fields = (
            'id', 'name', 'description', 'avg_rating', 'reviews_count',
            'is_active', 'created_at', 'category', 'tags', 'images', "discount", "categories",
            "set_images", 'can_choose_tags'
        )
        extra_kwargs = {
            'id': {'read_only': True},
            'avg_rating': {'read_only': True},
            'reviews_count': {'read_only': True},
            'created_at': {'read_only': True},
            'modified_at': {'read_only': True}
        }

    def get_discount(self, instance):
        promotion = instance.promotions.active_promotions().first()
        if not promotion:
            return

        try:
            return promotion.discount.percentage
        except ObjectDoesNotExist:
            return

    def validate(self, attrs):
        attrs = super().validate(attrs)
        if not self.instance:
            attrs['id'] = uid_generate()
            attrs['shop_code'] = "kaimono"
            attrs['shop_url'] = "https://kaimono.vip"
        return attrs

    def get_categories(self, instance):
        categories = instance.genres.exclude(level=0).filter(deactivated=False).order_by('-level')
        return CategoryAdminSerializer(instance=categories, many=True, context=self.context).data

    def create(self, validated_data):
        category = validated_data.pop('category', None)
        images = validated_data.pop('set_images', None)
        tags = validated_data.pop('tags', None)
        product = super().create(validated_data)
        if category:
            category_tree = recursive_single_tree(category, "parent")
            product.categories.add(category, *category_tree)
        if tags:
            product.tags.add(*tags)
        if images:
            ProductImage.objects.bulk_create([ProductImage(product=product, image=image) for image in images])
        return product

    def update(self, instance, validated_data):
        category = validated_data.pop('category', None)
        images = validated_data.pop('set_images', None)
        tags = validated_data.pop('tags', None)
        if category:
            category_tree = recursive_single_tree(category, "parent")
            instance.categories.clear()
            instance.categories.add(category, *category_tree)
        if tags:
            instance.tags.clear()
            instance.tags.add(*tags)
        if images:
            ProductImage.objects.filter(product=instance).delete()
            ProductImage.objects.bulk_create([ProductImage(product=instance, image=image) for image in images])
        return super().update(instance, validated_data)


class ProductReviewAdminSerializer(serializers.ModelSerializer):
    user = UserAdminSerializer(read_only=True)
    product = ShortProductAdminSerializer(many=False, read_only=True)
    product_id = serializers.PrimaryKeyRelatedField(queryset=Product.objects.all(), write_only=True, required=True)

    class Meta:
        model = ProductReview
        fields = ('id', 'user', 'product', 'product_id', 'rating', 'moderated', 'comment', 'created_at')


class BannerAdminSerializer(serializers.ModelSerializer):
    class Meta:
        model = Banner
        fields = '__all__'

    def validate(self, attrs):
        banner_type = attrs.get("type", "")
        link = attrs.get("link")
        if banner_type == Banner.Type.link and not link:
            raise serializers.ValidationError({"link": "required if banner type is %s" % Banner.Type.link.value})
        return attrs


class PromotionAdminSerializer(serializers.ModelSerializer):
    set_products = serializers.PrimaryKeyRelatedField(
        queryset=Product.objects.all(),
        write_only=True,
        many=True,
        required=False
    )
    set_discount = serializers.FloatField(validators=[MaxValueValidator(100)], write_only=True, required=False)
    discount = serializers.SlugRelatedField(slug_field='percentage', read_only=True)
    banner = BannerAdminSerializer(many=False, read_only=True)
    products = ShortProductAdminSerializer(many=True, read_only=True)

    type = serializers.ChoiceField(choices=Banner.Type.choices, default=Banner.Type.promotion, write_only=True)
    name = serializers.CharField(write_only=True, max_length=255, required=False)
    description = serializers.CharField(write_only=True, required=False)
    image = serializers.ImageField(write_only=True, required=True)
    link = serializers.URLField(write_only=True, required=False)

    class Meta:
        model = Promotion
        banner_fields = ("type", "name", "description", "image", "link")
        fields = ('id', 'site', 'discount', 'set_discount', 'products', 'set_products',
                  'deactivated', 'created_at', "banner", *banner_fields)
        extra_kwargs = {"site": {"required": True}}

    @staticmethod
    def validate_products_site(site, products) -> bool:
        return all(product.id.startswith(site) for product in products)

    def validate(self, attrs):
        products = attrs.get('set_products')
        if products:
            site = attrs.get('site')
            if not site and self.instance:
                site = self.instance.site

            if not self.validate_products_site(site, products):
                raise serializers.ValidationError({"set_products": _("All products must be for site %s" % site)})
        return attrs

    def collect_banner_data(self, validated_data) -> dict[str, Any]:
        banner_data = {}
        fields = list(validated_data.keys())
        for field in fields:
            if field in self.Meta.banner_fields:
                banner_data[field] = validated_data.pop(field)
        return banner_data

    def create(self, validated_data):
        banner_data = self.collect_banner_data(validated_data)
        banner_serializer = BannerAdminSerializer(data=banner_data, many=False, context=self.context)
        banner_serializer.is_valid(raise_exception=True)
        banner_serializer.save()
        validated_data['banner'] = banner_serializer.instance

        discount = validated_data.pop('set_discount', None)
        products = validated_data.pop('set_products', None)
        promotion = super().create(validated_data)
        banner_type = banner_data.get("type")
        match banner_type:
            case Banner.Type.promotion if products:
                promotion.products.add(*products)
                promotion.save()

        match banner_type:
            case Banner.Type.promotion if discount:
                Discount.objects.create(promotion=promotion, percentage=discount)
        return promotion

    def update(self, instance, validated_data):
        product_ids = validated_data.pop('set_products', None)
        if product_ids:
            instance.products.clear()
            instance.products.add(*product_ids)

        discount = validated_data.pop('set_discount', None)
        if discount:
            if not product_ids and not instance.products.exists():
                raise serializers.ValidationError(
                    {'set_discount': _('To indicate a discount, products must be selected'),
                     'product_ids': _('Is required')}
                )

            try:
                instance.discount.percentage = discount
                instance.discount.save()
            except ObjectDoesNotExist:
                Discount.objects.create(promotion=instance, percentage=discount)

        banner_data = self.collect_banner_data(validated_data)
        banner_serializer = BannerAdminSerializer(
            instance=instance.banner,
            data=banner_data,
            partial=self.partial,
            many=False,
            context=self.context
        )
        banner_serializer.is_valid(raise_exception=True)
        banner_serializer.save()
        return super().update(instance, validated_data)


class OrderCustomerAdminSerializer(serializers.ModelSerializer):
    class Meta:
        model = Customer
        fields = ('id', 'bayer_code', 'name', 'email')


class DeliveryAddressAdminSerializer(serializers.ModelSerializer):
    user = UserAdminSerializer(read_only=True)

    class Meta:
        model = DeliveryAddress
        fields = '__all__'


class ReceiptAdminSerializer(serializers.ModelSerializer):
    inventory = serializers.PrimaryKeyRelatedField(
        queryset=ProductInventory.objects.all(),
        many=False,
        write_only=True
    )
    unit_price = OrderConversionField(read_only=True, all_conversions=True)
    site_price = OrderConversionField(read_only=True, all_conversions=True)
    total_price = OrderConversionField(read_only=True, all_conversions=True)

    class Meta:
        model = Receipt
        fields = ('id', 'inventory', 'product_name', 'product_image', 'product_url',
                  'quantity', 'unit_price', 'total_price', 'site_price', 'discount', 'site_currency')
        extra_kwargs = {
            'product_name': {'read_only': True},
            'product_image': {'read_only': True},
            'product_url': {'read_only': True},
            'site_currency': {'read_only': True}
        }

    def validate(self, attrs):
        inventory = attrs.pop('inventory', None)
        if inventory:
            attrs['unit_price'] = inventory.price
            product = inventory.product
            promotion = product.promotions.active_promotions().first()
            if promotion:
                try:
                    attrs['discount'] = promotion.discount.percentage
                except ObjectDoesNotExist:
                    attrs['discount'] = 0.0

            image = product.images.first()
            attrs['shop_url'] = product.shop_url
            attrs['product_code'] = product.id
            attrs['product_url'] = inventory.product_url
            if inventory.id.startswith('uniqlo'):
                attrs['product_name'] = product.name
            else:
                attrs['product_name'] = inventory.name
            attrs['product_image'] = image.url if image else None
            attrs['site_currency'] = get_currency_by_id(product.id)
            attrs['site_price'] = inventory.site_price
            attrs['tags'] = ', '.join(inventory.tags.values_list('name', flat=True))
        return attrs


class OrderShippingSerializer(serializers.ModelSerializer):
    class Meta:
        model = OrderShipping
        fields = ('shipping_carrier', 'qrcode_image')


class OrderConversionSerializer(serializers.ModelSerializer):
    class Meta:
        model = OrderConversion
        fields = "__all__"


class BaseOrderAdminSerializer(serializers.ModelSerializer):
    customer = OrderCustomerAdminSerializer(read_only=True)
    total_price = serializers.SerializerMethodField(read_only=True)
    country_code = serializers.SerializerMethodField(read_only=True)

    class Meta:
        model = Order
        fields = ("id", "customer", "comment", "status", "customer", "total_price", "created_at", "country_code")

    def get_country_code(self, instance):
        return instance.delivery_address.country_code

    def get_total_price(self, instance):
        total_price = 0.0

        for receipt in instance.receipts.all():
            price = receipt.total_price

            if receipt.site_currency != Currencies.yen:
                price_per = order_currencies_price_per(
                    order_id=receipt.order_id,
                    currency_from=receipt.site_currency,
                    currency_to=Currencies.yen
                )
                price = convert_price(price, price_per) if price_per else 0.0

            if not price:
                continue

            total_price += float(price)
        return total_price


class PaymentSerializer(serializers.ModelSerializer):
    class Meta:
        model = Payment
        fields = ("payment_type", "payment_link", "qrcode", "created_at")


class OrderAdminSerializer(BaseOrderAdminSerializer):
    payment = PaymentSerializer(many=False, read_only=True)
    shipping_detail = OrderShippingSerializer(many=False, read_only=True)
    delivery_address = DeliveryAddressAdminSerializer(read_only=True, many=False)
    receipts = ReceiptAdminSerializer(many=True, read_only=True)
    conversions = OrderConversionSerializer(many=True, read_only=True)

    class Meta:
        model = Order
        fields = ('id', 'status', 'comment', 'customer', 'receipts', 'delivery_address', 'shipping_detail',
                  "conversions", "total_price", "created_at", 'payment')


# ------------------------------------------------- Analytics ----------------------------------------------------------
class OrderAnalyticsSerializer(AnalyticsSerializer):
    status = serializers.MultipleChoiceField(choices=Order.Status.choices, write_only=True)

    class Meta:
        model = Order
        fields = ('status',)
        empty_template = {"receipts_info": [], "count": 0}
        start_field = 'created_at__date'
        end_field = 'created_at__date'


class UserAnalyticsSerializer(AnalyticsSerializer):
    AVAILABLE_ROLES = (User.Role.CLIENT,)
    is_active = serializers.BooleanField(required=False, write_only=True)
    registration_payed = serializers.BooleanField(required=False, write_only=True)
    email_confirmed = serializers.BooleanField(required=False, write_only=True)

    class Meta:
        model = User
        fields = ('is_active', 'registration_payed', 'email_confirmed')
        empty_template = {"users": [], "count": 0}
        start_field = 'date_joined__date'
        end_field = 'date_joined__date'

    def build_queries(self) -> dict[str, Any]:
        queries = super().build_queries()
        queries['role__in'] = self.AVAILABLE_ROLES
        return queries

    def users_representation(self, users):
        request = self.context['request']
        for user in users:
            image = user.get('image')
            if image:
                user['image'] = request.build_absolute_uri(image)
        return users

    def to_representation(self, df):
        if df.empty is False:
            df['users'] = df['users'].apply(lambda x: self.users_representation(x))
        return super().to_representation(df)


class ReviewAnalyticsSerializer(AnalyticsSerializer):
    moderated = serializers.BooleanField(required=False, write_only=True)

    class Meta:
        model = ProductReview
        fields = ('moderated',)
        empty_template = {'info': [], 'count': 0, 'avg_rating': 0.0}
        start_field = 'created_at__date'
        end_field = 'created_at__date'
