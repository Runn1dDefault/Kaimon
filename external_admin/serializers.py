from typing import Any

from django.core.validators import MaxValueValidator
from django.db import transaction
from django.db.models import F
from django.utils.timezone import localtime
from rest_framework import serializers

from currencies.mixins import CurrencySerializerMixin
from currencies.models import Conversion
from product.models import Product, Genre, Tag, ProductImageUrl, TagGroup, ProductReview
from product.serializers import TagByGroupSerializer
from product.utils import get_genre_parents_tree
from promotions.models import Banner, Promotion, Discount
from order.models import Order, Country
from order.serializers import ProductReceiptSerializer
from users.models import User
from utils.helpers import round_half_integer


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


class TagAdminSerializer(serializers.ModelSerializer):
    class Meta:
        model = Tag
        fields = '__all__'


class GenreAdminSerializer(serializers.ModelSerializer):
    class Meta:
        model = Genre
        fields = '__all__'


class ProductImageAdminSerializer(serializers.ModelSerializer):
    product = serializers.PrimaryKeyRelatedField(queryset=Product.objects.all(), write_only=True, required=True)
    url = serializers.URLField(required=True)

    class Meta:
        model = ProductImageUrl
        fields = ('id', 'product', 'url')


class ProductAdminSerializer(CurrencySerializerMixin, serializers.ModelSerializer):
    sale_price = serializers.SerializerMethodField(read_only=True)
    image_urls = serializers.SlugRelatedField(many=True, read_only=True, slug_field='url')

    class Meta:
        model = Product
        fields = ('id', 'name', 'price', 'sale_price', 'availability', 'avg_rank', 'reviews_count', 'image_urls',
                  'created_at', 'description')

    def get_sale_price(self, instance):
        sale_price = instance.sale_price
        if not sale_price:
            return

        som_conversion = self.get_conversation_instance(Conversion.Currencies.som)
        dollar_conversion = self.get_conversation_instance(Conversion.Currencies.dollar)
        return {
            Conversion.Currencies.yen: sale_price,
            Conversion.Currencies.som: som_conversion.calc_price(sale_price),
            Conversion.Currencies.dollar: dollar_conversion.calc_price(sale_price)
        }


class TagByGroupAdminSerializer(TagByGroupSerializer):
    class Meta:
        model = TagGroup
        fields = '__all__'


class ProductDetailAdminSerializer(ProductAdminSerializer):
    product_url = serializers.URLField(required=False)
    genre = serializers.PrimaryKeyRelatedField(queryset=Genre.objects.exclude(level=0), many=False, write_only=True,
                                               required=True)
    tags = serializers.PrimaryKeyRelatedField(
        queryset=Tag.objects.all(),
        write_only=True,
        required=False,
        many=True
    )
    image_urls = ProductImageAdminSerializer(many=True, read_only=True)
    images = serializers.ListField(child=serializers.URLField(), write_only=True, required=False)
    tags_info = serializers.SerializerMethodField(read_only=True)

    class Meta:
        model = Product
        fields = (
            *ProductAdminSerializer.Meta.fields, 'name_ru', 'name_en', 'name_tr', 'name_ky', 'name_kz',
            'description_ru', 'description_en', 'description_tr', 'description_ky', 'description_kz',
            'is_active', 'tags_info', 'reference_rank', 'genre', 'tags', 'images', 'product_url'
        )
        extra_kwargs = {'id': {'read_only': True}, 'price': {'required': True}}

    def get_tags_info(self, instance):
        if not instance.tags.exists():
            return
        group_ids = list(instance.tags.all().order_by('group_id')
                                            .distinct('group_id')
                                            .values_list('group_id', flat=True))
        return TagByGroupAdminSerializer(
            tag_ids=list(instance.tags.values_list('id', flat=True)),
            instance=TagGroup.objects.filter(id__in=group_ids),
            many=True,
            context=self.context
        ).data

    def create(self, validated_data):
        images = validated_data.pop('images', None)
        genre = validated_data.pop('genre')
        tags = validated_data.pop('tags', None)
        genres_tree = get_genre_parents_tree(genre)

        with transaction.atomic():
            product = super().create(validated_data)
            product.genres.add(*genres_tree)
            if images:
                ProductImageUrl.objects.bulk_create([ProductImageUrl(product=product, url=url) for url in images])
            if tags:
                product.tags.add(*tags)
            product.save()
        return product

    def update(self, instance, validated_data):
        genre = validated_data.pop('genre', None)
        tags = validated_data.pop('tags', None)
        product = super().update(instance, validated_data)
        save = False
        if genre:
            genres_tree = get_genre_parents_tree(genre)
            product.genres.clear()
            product.genres.add(*genres_tree)
            save = True
        if tags:
            product.tags.clear()
            product.tags.add(*tags)
            save = True
        if save:
            product.save()
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

    set_products = serializers.PrimaryKeyRelatedField(queryset=Product.objects.all(), write_only=True, many=True)
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

        with transaction.atomic():
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
        discount = validated_data.pop('set_discount', None)
        if discount:
            instance.discount.percentage = discount
            instance.discount.save()
        product_ids = validated_data.pop('product_ids', None)
        if product_ids:
            instance.products.clear()
            instance.products.add(*product_ids)
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


class CountryAdminSerializer(serializers.ModelSerializer):
    class Meta:
        model = Country
        fields = '__all__'


class OrderAdminSerializer(serializers.ModelSerializer):
    email = serializers.SerializerMethodField(read_only=True)
    full_name = serializers.SerializerMethodField(read_only=True)
    total_price = serializers.SerializerMethodField(read_only=True)
    date = serializers.SerializerMethodField(read_only=True)
    country = CountryAdminSerializer(many=False, read_only=True)
    city = serializers.SerializerMethodField(read_only=True)
    address = serializers.SerializerMethodField(read_only=True)
    phone = serializers.SerializerMethodField(read_only=True)
    zip_code = serializers.SerializerMethodField(read_only=True)
    receipts = ProductReceiptSerializer(many=True, read_only=True)

    class Meta:
        model = Order
        fields = ('id', 'status', 'email', 'full_name', 'total_price', 'date', 'country', 'city', 'phone', 'zip_code',
                  'address', 'receipts')

    def get_email(self, instance):
        return instance.delivery_address.user.email

    def get_full_name(self, instance):
        return instance.delivery_address.user.full_name

    def get_total_price(self, instance):
        receipts = instance.receipts.filter(is_canceled=False, qty__gt=0, unit_price__gt=0)
        return sum(
            receipts.annotate(
                total_price=F('unit_price') * F('qty')
            ).values_list('total_price', flat=True)
        )

    def get_date(self, instance):
        return localtime(instance.created_at).date()

    def get_city(self, instance):
        return instance.delivery_address.city

    def get_address(self, instance):
        return instance.delivery_address.address

    def get_phone(self, instance):
        return instance.delivery_address.phone
