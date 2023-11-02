from django.core.exceptions import ObjectDoesNotExist
from rest_framework import serializers

from .models import Banner, Promotion


class BannerSerializer(serializers.ModelSerializer):
    class Meta:
        model = Banner
        fields = ('id', 'name', 'description', 'image')


class PromotionSerializer(serializers.ModelSerializer):
    banner = BannerSerializer(many=False, read_only=True)
    discount = serializers.SerializerMethodField(read_only=True)
    products_count = serializers.SerializerMethodField(read_only=True)

    def __init__(self, *args, **kwargs):
        kwargs['many'] = True
        super().__init__(*args, **kwargs)

    class Meta:
        model = Promotion
        fields = ('id', 'banner', 'discount', 'created_at', 'start_date', 'end_date', 'products_count')

    def get_discount(self, instance):
        try:
            return instance.discount.percentage
        except ObjectDoesNotExist:
            return None

    def get_products_count(self, instance) -> int:
        return instance.products.filter(is_active=True).count()
