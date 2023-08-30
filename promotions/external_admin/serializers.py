from django.db import transaction
from django.utils.translation import gettext_lazy as _
from rest_framework import serializers

from product.models import Product
from promotions.models import Banner, Promotion, Discount
from promotions.serializers import PromotionDetailSerializer


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
