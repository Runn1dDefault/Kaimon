from typing import Any

from django.core.exceptions import ObjectDoesNotExist
from django.core.validators import MaxValueValidator
from django.utils.translation import gettext_lazy as _
from rest_framework import serializers

from currencies.models import Conversion
from currencies.serializers import ConversionField
from product.models import Product, Genre, Tag, ProductImageUrl, TagGroup, ProductReview, ProductGenre, ProductTag
from product.utils import get_genre_parents_tree
from promotions.models import Banner, Promotion, Discount
from order.models import Order, Customer, DeliveryAddress, Receipt
from users.models import User
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


class TagGroupAdminSerializer(serializers.ModelSerializer):
    class Meta:
        model = TagGroup
        fields = ('id', 'name', 'name_ru', 'name_en', 'name_tr', 'name_ky', 'name_kz')


class TagAdminSerializer(serializers.ModelSerializer):
    class Meta:
        model = Tag
        fields = ('id', 'name', 'name_ru', 'name_en', 'name_tr', 'name_ky', 'name_kz')


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
                  'reference_rank', 'description', 'image_urls')


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
    tags_info = serializers.SerializerMethodField(read_only=True)

    class Meta:
        model = Product
        fields = (
            *ProductAdminSerializer.Meta.fields, 'name_ru', 'name_en', 'name_tr', 'name_ky', 'name_kz',
            'description_ru', 'description_en', 'description_tr', 'description_ky', 'description_kz',
            'genres', 'tags_info', 'genre', 'tags', 'images', 'product_url'
        )
        extra_kwargs = {'id': {'read_only': True}, 'price': {'required': True}}

    def get_genres(self, instance):
        genres_fk = instance.genres.filter(genre__deactivated=False)
        if not genres_fk.exists():
            return []

        genres = (
            Genre.objects.exclude(level=0)
            .filter(id__in=genres_fk.values_list('genre_id', flat=True))
            .order_by('-level')
        )
        return GenreAdminSerializer(instance=genres, many=True, context=self.context).data

    def get_tags_info(self, instance):
        tags_fk = instance.tags.all()
        if not tags_fk.exists():
            return []

        group_ids = (
            tags_fk.order_by('tag__group_id')
                   .distinct('tag__group_id')
                   .values_list('tag__group_id', flat=True)
        )
        groups_queryset = TagGroup.objects.filter(id__in=group_ids)
        return groups_queryset.tags_data(tag_ids=tags_fk.values_list('tag_id', flat=True))

    @staticmethod
    def update_genres(instance, genre) -> list[ProductGenre]:
        genres_query = ProductGenre.objects.filter(product=instance)
        if genres_query.exists():
            genres_query.delete()
        genres_tree = get_genre_parents_tree(genre)
        return ProductGenre.objects.bulk_create(
            [ProductGenre(product=instance, genre_id=genre_id) for genre_id in genres_tree]
        )

    @staticmethod
    def update_tags(instance, tags) -> list[ProductTag]:
        tags_query = ProductTag.objects.filter(product=instance)
        if tags_query.exists():
            tags_query.delete()
        return ProductTag.objects.bulk_create(
            [ProductTag(product=instance, tag=tag) for tag in tags]
        )

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
        product = super().save()
        if genre:
            self.update_genres(product, genre)
        if tags:
            self.update_tags(product, tags)
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
    name_ru = serializers.CharField(write_only=True, required=False)
    name_en = serializers.CharField(write_only=True, required=False)
    name_tr = serializers.CharField(write_only=True, required=False)
    name_kz = serializers.CharField(write_only=True, required=False)
    name_ky = serializers.CharField(write_only=True, required=False)
    description = serializers.CharField(write_only=True, required=False)
    description_ru = serializers.CharField(write_only=True, required=False)
    description_en = serializers.CharField(write_only=True, required=False)
    description_tr = serializers.CharField(write_only=True, required=False)
    description_kz = serializers.CharField(write_only=True, required=False)
    description_ky = serializers.CharField(write_only=True, required=False)
    image = serializers.ImageField(write_only=True, required=False)

    set_products = serializers.PrimaryKeyRelatedField(queryset=Product.objects.all(), write_only=True, many=True,
                                                      required=False)
    set_discount = serializers.FloatField(validators=[MaxValueValidator(100)], write_only=True, required=False)

    discount = serializers.SlugRelatedField(slug_field='percentage', read_only=True)
    banner = BannerAdminSerializer(many=False, read_only=True)
    products = ProductAdminSerializer(many=True, read_only=True)

    class Meta:
        model = Promotion
        banner_fields = ('name', 'name_ru', 'name_en', 'name_tr', 'name_ky', 'name_kz', 'description',
                         'description_ru', 'description_en', 'description_tr', 'description_ky', 'description_kz',
                         'image')
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
        product_ids = validated_data.pop('product_ids', None)
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
    class Meta:
        model = Receipt
        fields = '__all__'


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
        prices = Order.analytics.filter(id=instance.id).total_prices().values('yen', 'som', 'dollar')
        return list(prices)[0]


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
    AVAILABLE_ROLES = (User.Role.CLIENT, User.Role.MANAGER, User.Role.DIRECTOR)
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
