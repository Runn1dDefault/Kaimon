from typing import Any

from django.core.exceptions import ObjectDoesNotExist
from django.core.validators import MaxValueValidator
from django.utils.translation import gettext_lazy as _
from rest_framework import serializers

from currencies.models import Conversion
from currencies.serializers import ConversionField
from currencies.utils import get_currency_price_per
from product.models import Product, Genre, Tag, ProductImageUrl, TagGroup, ProductReview
from promotions.models import Banner, Promotion, Discount
from order.models import Order, Customer, DeliveryAddress, Receipt
from users.models import User
from utils.helpers import recursive_single_tree
from utils.serializers import AnalyticsSerializer


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
        get_currency_price_per.cache_clear()
        return instance


class TagGroupAdminSerializer(serializers.ModelSerializer):
    class Meta:
        model = TagGroup
        fields = ('id', 'name')


class TagAdminSerializer(serializers.ModelSerializer):
    class Meta:
        model = Tag
        fields = ('id', 'name')


class ProductImageAdminSerializer(serializers.ModelSerializer):
    product = serializers.PrimaryKeyRelatedField(queryset=Product.objects.all(), write_only=True, required=True)
    url = serializers.URLField(required=True)

    class Meta:
        model = ProductImageUrl
        fields = ('id', 'product', 'url')


class GenreAdminSerializer(serializers.ModelSerializer):
    class Meta:
        model = Genre
        fields = '__all__'


class ProductAdminSerializer(serializers.ModelSerializer):
    price = ConversionField(all_conversions=True)
    sale_price = ConversionField(all_conversions=True, read_only=True)
    image_urls = serializers.SlugRelatedField(many=True, read_only=True, slug_field='url')

    class Meta:
        model = Product
        fields = ('id', 'name', 'price', 'sale_price', 'availability', 'is_active', 'avg_rank', 'reviews_count',
                  'description', 'image_urls')


class ProductDetailAdminSerializer(ProductAdminSerializer):
    product_url = serializers.URLField(required=False)
    genre = serializers.PrimaryKeyRelatedField(
        queryset=Genre.objects.exclude(level=0),
        many=False,
        write_only=True,
        required=True
    )
    tags = serializers.PrimaryKeyRelatedField(
        queryset=Tag.objects.all(),
        many=True,
        write_only=True,
        required=False,
    )
    images = serializers.ListField(child=serializers.URLField(), write_only=True, required=False)
    genres = serializers.SerializerMethodField(read_only=True)
    image_urls = serializers.SlugRelatedField(many=True, read_only=True, slug_field='url')

    class Meta:
        model = Product
        fields = (
            'id', 'name', 'price', 'sale_price', 'availability', 'is_active', 'avg_rank', 'reviews_count',
            'description', 'image_urls', 'genres', 'genre', 'tags', 'images', 'product_url', 'increase_percentage'
        )
        extra_kwargs = {
            'id': {'read_only': True},
            'price': {'required': True},
            'avg_rank': {'read_only': True},
            'reviews_count': {'read_only': True},
        }

    def validate(self, attrs):
        attrs = super().validate(attrs)
        price = attrs.pop('price', None)
        if price:
            attrs['rakuten_price'] = price
        return attrs

    def get_genres(self, instance):
        genres = instance.genres.exclude(level=0).filter(deactivated=False).order_by('-level')
        return GenreAdminSerializer(instance=genres, many=True, context=self.context).data

    @staticmethod
    def update_images(instance, image_urls) -> list[ProductImageUrl]:
        images_query = ProductImageUrl.objects.filter(product=instance)
        if images_query.exists():
            images_query.delete()
        return ProductImageUrl.objects.bulk_create(
            [ProductImageUrl(product=instance, url=url) for url in image_urls]
        )

    def save(self, **kwargs):
        genre = self.validated_data.pop('genre', None)
        images = self.validated_data.pop('images', None)
        tags = self.validated_data.pop('tags', None)
        product = super().save(**kwargs)
        if genre:
            print('Genre: ', genre)
            genres_tree = recursive_single_tree(genre, "parent")
            product.genres.clear()
            product.genres.add(*genres_tree)
        if tags:
            print('Tags: ', tags)
            product.tags.clear()
            product.tags.add(*tags)
        if images:
            self.update_images(product, images)
        return product


class ProductReviewAdminSerializer(serializers.ModelSerializer):
    user = UserAdminSerializer(read_only=True)
    product = ProductAdminSerializer(many=False, read_only=True)
    product_id = serializers.PrimaryKeyRelatedField(queryset=Product.objects.all(), write_only=True, required=True)

    class Meta:
        model = ProductReview
        fields = ('id', 'user', 'product', 'product_id', 'rank', 'is_read', 'is_active', 'comment', 'created_at')


class BannerAdminSerializer(serializers.ModelSerializer):
    class Meta:
        model = Banner
        fields = '__all__'


class PromotionAdminSerializer(serializers.ModelSerializer):
    name = serializers.CharField(write_only=True, required=True)
    description = serializers.CharField(write_only=True, required=False)
    image = serializers.ImageField(write_only=True, required=False)

    set_products = serializers.PrimaryKeyRelatedField(queryset=Product.objects.all(), write_only=True, many=True,
                                                      required=False)
    set_discount = serializers.FloatField(validators=[MaxValueValidator(100)], write_only=True, required=False)
    discount = serializers.SlugRelatedField(slug_field='percentage', read_only=True)
    banner = BannerAdminSerializer(many=False, read_only=True)
    products = ProductAdminSerializer(many=True, read_only=True)

    class Meta:
        model = Promotion
        banner_fields = ('name', 'description', 'image')
        fields = ('id', 'discount', 'set_discount', 'banner', 'products', 'set_products', 'start_date', 'end_date',
                  'deactivated', 'created_at', *banner_fields)

    def collect_banner_data(self, validated_data) -> dict[str, Any]:
        banner_data = {}
        fields = list(validated_data.keys())
        for field in fields:
            if field in self.Meta.banner_fields:
                banner_data[field] = validated_data.pop(field)
        return banner_data

    def create(self, validated_data):
        discount = validated_data.pop('set_discount', None)
        products = validated_data.pop('set_products', None)
        banner_data = self.collect_banner_data(validated_data)
        banner_serializer = BannerAdminSerializer(data=banner_data, many=False, context=self.context)
        banner_serializer.is_valid(raise_exception=True)
        banner_serializer.save()
        validated_data['banner_id'] = banner_serializer.instance.id
        promotion = super().create(validated_data)
        if discount:
            Discount.objects.create(promotion=promotion, percentage=discount)
        if products:
            promotion.products.add(*products)
            promotion.save()
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
        fields = ('id', 'name', 'email', 'phone')


class DeliveryAddressAdminSerializer(serializers.ModelSerializer):
    user = UserAdminSerializer(read_only=True)

    class Meta:
        model = DeliveryAddress
        fields = '__all__'


class ReceiptAdminSerializer(serializers.ModelSerializer):
    product_name = serializers.SerializerMethodField(read_only=True)
    images = serializers.SerializerMethodField(read_only=True)
    total_prices = serializers.SerializerMethodField(read_only=True)

    class Meta:
        model = Receipt
        fields = ['id', 'product', 'product_name', 'images', 'discount', 'quantity', 'unit_price', 'total_prices']

    def get_product_name(self, instance):
        return instance.product.name

    def get_images(self, instance):
        product_images = instance.product.image_urls
        if not product_images.exists():
            return []
        return list(product_images.values_list('url', flat=True))

    def get_total_prices(self, instance):
        unit_price = instance.unit_price
        if instance.discount > 0:
            per = (instance.discount * 100) / instance.discount
            unit_price = unit_price - per

        price = unit_price * instance.quantity

        return {
            'yen': price,
            'som': price * instance.order.yen_to_som,
            'dollar': price * instance.order.yen_to_usd
        }


class OrderAdminSerializer(serializers.ModelSerializer):
    customer = OrderCustomerAdminSerializer(read_only=True)
    delivery_address = DeliveryAddressAdminSerializer(read_only=True)
    total_prices = serializers.SerializerMethodField(read_only=True)
    receipts = ReceiptAdminSerializer(many=True, read_only=True)

    class Meta:
        model = Order
        fields = ('id', 'status', 'comment', 'shipping_weight', 'total_prices', 'customer', 'receipts',
                  'delivery_address')

    def get_total_prices(self, instance):
        return list(Order.analytics.filter(id=instance.id).total_prices().values('yen', 'som', 'dollar'))[0]


# ------------------------------------------------- Analytics ----------------------------------------------------------
class OrderAnalyticsSerializer(AnalyticsSerializer):
    status = serializers.MultipleChoiceField(choices=Order.Status.choices, write_only=True)

    class Meta:
        model = Order
        fields = ('status',)
        hide_fields = ('sale_prices_yen', 'sale_prices_som', 'sale_prices_dollar')
        empty_template = {"receipts_info": [], "yen": 0, "som": 0, "dollar": 0, "count": 0}
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
    is_read = serializers.BooleanField(required=False, write_only=True)
    is_active = serializers.BooleanField(required=False, write_only=True)

    class Meta:
        model = ProductReview
        fields = ('is_read', 'is_active')
        empty_template = {'info': [], 'count': 0, 'avg_rank': 0.0}
        start_field = 'created_at__date'
        end_field = 'created_at__date'
