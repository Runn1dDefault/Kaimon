from typing import Any

from django.core.validators import MaxValueValidator
from django.db import transaction
from django.db.models import F
from django.utils.timezone import localtime
from django.utils.translation import gettext_lazy as _
from rest_framework import serializers

from currencies.models import Conversion
from product.models import Product, Genre, Tag, ProductImageUrl
from product.serializers import ProductListSerializer, ProductRetrieveSerializer
from product.utils import get_genre_parents_tree
from promotions.models import Banner, Promotion, Discount
from order.models import Order
from order.serializers import ProductReceiptSerializer
from users.models import User
from utils.mixins import LangSerializerMixin


class UserAdminSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ('email', 'full_name', 'role', 'is_active', 'date_joined', 'last_login', 'registration_payed')
        extra_kwargs = {'role': {'read_only': True}}


class OrderAdminSerializer(LangSerializerMixin, serializers.ModelSerializer):
    email = serializers.SerializerMethodField(read_only=True)
    full_name = serializers.SerializerMethodField(read_only=True)
    total_price = serializers.SerializerMethodField(read_only=True)
    date = serializers.SerializerMethodField(read_only=True)
    country = serializers.SerializerMethodField(read_only=True)
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

    def get_country(self, instance):
        country = instance.delivery_address.country
        return getattr(country, self.get_translate_field('name')) or country.name

    def get_city(self, instance):
        return instance.delivery_address.city

    def get_address(self, instance):
        return instance.delivery_address.address

    def get_phone(self, instance):
        return instance.delivery_address.phone


class ConversionAdminSerializer(serializers.ModelSerializer):
    class Meta:
        model = Conversion
        fields = ('id', 'currency_from', 'currency_to', 'price_per')
        extra_kwargs = {'currency_from': {'read_only': True}, 'currency_to': {'read_only': True}}


class ProductAdminSerializer(ProductListSerializer):
    class Meta(ProductListSerializer.Meta):
        fields = ProductListSerializer.Meta.fields + ['description']
        translate_fields = ProductListSerializer.Meta.translate_fields + ['description']


class ProductImageAdminSerializer(serializers.ModelSerializer):
    url = serializers.URLField(required=True)

    class Meta:
        model = ProductImageUrl
        fields = ('id', 'product', 'url')
        extra_fields = {'product': {'write_only': True, 'required': True}}

    def validate(self, attrs):
        if not Product.objects.filter(id=attrs['product']).exists():
            raise serializers.ValidationError({'product': _('Does not exist!')})
        return attrs


class ProductDetailAdminSerializer(ProductRetrieveSerializer):
    product_url = serializers.URLField(required=False)
    genre = serializers.IntegerField(write_only=True, required=True)
    tags = serializers.PrimaryKeyRelatedField(queryset=Tag.objects.all(), write_only=True, required=False)
    image_urls = ProductImageAdminSerializer(many=True, read_only=True)
    set_image_urls = serializers.ListSerializer(child=serializers.URLField(), many=True, required=False,
                                                write_only=True)
    # TODO: change!

    class Meta:
        model = Product
        fields = ('id', 'name', 'price', 'sale_price', 'is_active', 'availability', 'avg_rank', 'reviews_count',
                  'image_urls', 'created_at', 'description', 'tags_info', 'reference_rank', 'genre', 'tags',
                  'product_url',)
        extra_kwargs = {'id': {'read_only': True}}

    def validate(self, attrs):
        genre_id = attrs.get('genre')
        if genre_id:
            genre_search = Genre.objects.exlude(level=0).filter(id=genre_id)
            if not genre_search.exists():
                raise serializers.ValidationError({'genre': _('Genre does not exists!')})
            attrs['genre'] = genre_search.first()
        tag_ids = attrs.get('tags')
        if tag_ids and not Tag.objects.filter(id__in=tag_ids).exists():
            raise serializers.ValidationError({'tags': _('Some tags not exists!')})
        return attrs

    def create(self, validated_data):
        images = validated_data.pop('image_urls', None)
        genre = validated_data.pop('genre')
        tags = validated_data.pop('tags')
        genres_tree = get_genre_parents_tree(genre)

        with transaction.atomic():
            product = super().create(validated_data)
            if images:
                images_data = [{'product': product.id} | image_data for image_data in images]
                serializer = ProductImageAdminSerializer(data=images_data, many=True)
                serializer.is_valid(raise_exception=True)
                serializer.save()
            product.genres.add(*genres_tree)
            product.tags.add(*tags)
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
        banner_fields = ['name', 'name_ru', 'name_en', 'name_tr', 'name_ky', 'name_kz', 'description',
                         'description_ru', 'description_en', 'description_tr', 'description_ky', 'description_kz',
                         'image']
        fields = ['id', 'discount', 'set_discount', 'banner', 'products', 'set_products', 'start_date', 'end_date',
                  'deactivated', 'created_at'] + banner_fields

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
