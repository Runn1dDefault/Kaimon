from django.db import transaction
from django.db.models import F
from django.utils.timezone import localtime
from django.utils.translation import gettext_lazy as _
from rest_framework import serializers

from currencies.models import Conversion
from product.models import Product
from promotions.models import Banner, Promotion, Discount
from promotions.serializers import PromotionDetailSerializer
from order.models import Order
from order.serializers import ProductReceiptSerializer
from users.models import User
from utils.mixins import LangSerializerMixin


class AdminUserSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ('email', 'full_name', 'role', 'is_active', 'date_joined')
        extra_kwargs = {'role': {'read_only': True}}


class AdminOrderSerializer(LangSerializerMixin, serializers.ModelSerializer):
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


class BannerAdminSerializer(serializers.ModelSerializer):
    class Meta:
        model = Banner
        fields = ('id', 'name', 'name_ru', 'name_ky', 'name_en', 'name_tr', 'name_kz', 'description',
                  'description_ru', 'description_en', 'description_ky', 'description_kz', 'description_tr', 'image')


class PromotionAdminSerializer(PromotionDetailSerializer):
    banner = BannerAdminSerializer(many=False)


class PromotionCreateSerializer(serializers.Serializer):
    name = serializers.CharField(max_length=255, required=True, write_only=True)
    name_ru = serializers.CharField(max_length=255, required=False, write_only=True)
    name_en = serializers.CharField(max_length=255, required=False, write_only=True)
    name_tr = serializers.CharField(max_length=255, required=False, write_only=True)
    name_ky = serializers.CharField(max_length=255, required=False, write_only=True)
    name_kz = serializers.CharField(max_length=255, required=False, write_only=True)

    start_date = serializers.DateField(required=True, write_only=True)
    end_date = serializers.DateField(required=True, write_only=True)

    description = serializers.CharField(required=False, write_only=True)
    description_ru = serializers.CharField(required=False, write_only=True)
    description_en = serializers.CharField(required=False, write_only=True)
    description_tr = serializers.CharField(required=False, write_only=True)
    description_ky = serializers.CharField(required=False, write_only=True)
    description_kz = serializers.CharField(required=False, write_only=True)

    image = serializers.ImageField(required=False, allow_null=True, write_only=True)
    products = serializers.ListSerializer(required=False, child=serializers.IntegerField(),
                                          allow_empty=True, write_only=True)
    discount = serializers.FloatField(required=False, write_only=True)

    def validate(self, attrs):
        start_date, end_date = attrs.pop('start_date'), attrs.pop('end_date')
        if start_date >= end_date:
            raise serializers.ValidationError({'detail': _('start_date cannot be greater than or equal to end_date')})

        products = attrs.pop('products', [])
        if products:
            products_queryset = Product.objects.filter(id__in=products)
            if not products_queryset.exists():
                raise serializers.ValidationError({'detail': _('Products not found!')})

        discount = attrs.pop('discount')
        with transaction.atomic():
            banner = Banner.objects.create(**attrs)
            promotion = Promotion.objects.create(
                banner=banner,
                start_date=start_date,
                end_date=end_date
            )
            if products:
                promotion.products.add(*products)
                promotion.save()
            if discount:
                Discount.objects.create(promotion=promotion, percentage=discount)
        return PromotionAdminSerializer(instance=promotion, many=False, context=self.context).data


class AdminConversionSerializer(serializers.ModelSerializer):
    class Meta:
        model = Conversion
        fields = ('id', 'currency_from', 'currency_to', 'price_per')
        extra_kwargs = {'currency_from': {'read_only': True}, 'currency_to': {'read_only': True}}
