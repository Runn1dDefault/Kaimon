from django.core.exceptions import ObjectDoesNotExist
from rest_framework import serializers

from product.serializers import ProductSerializer
from utils.mixins import LangSerializerMixin

from .models import Banner, Promotion


class BannerSerializer(LangSerializerMixin, serializers.ModelSerializer):
    class Meta:
        model = Banner
        fields = ('id', 'name', 'description', 'image')
        translate_fields = ('name', 'description')


class PromotionSerializer(serializers.ModelSerializer):
    banner = BannerSerializer(many=False, read_only=True)
    discount = serializers.SerializerMethodField(read_only=True)

    class Meta:
        model = Promotion
        fields = ('id', 'banner', 'discount', 'created_at')

    def get_discount(self, instance):
        try:
            return instance.discount.percentage
        except ObjectDoesNotExist:
            return None


class PromotionDetailSerializer(PromotionSerializer):
    product_serializer_class = ProductSerializer
    products = serializers.SerializerMethodField(read_only=True)

    class Meta:
        model = Promotion
        fields = ('id', 'banner', 'discount', 'created_at', 'start_date', 'end_date', 'products')

    def get_products(self, instance):
        return self.product_serializer_class(
            instance=instance.products.filter(is_active=True),
            many=True,
            context=self.context
        ).data
