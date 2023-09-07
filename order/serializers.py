from django.db import transaction
from django.utils.translation import gettext_lazy as _
from rest_framework import serializers

from product.models import Product
from utils.mixins import LangSerializerMixin

from .models import Order, UserDeliveryAddress, Country, ProductReceipt


class CountrySerializer(LangSerializerMixin, serializers.ModelSerializer):
    class Meta:
        model = Country
        fields = ('id', 'name')
        translate_fields = ('name',)


class DeliveryAddressSerializer(serializers.ModelSerializer):
    country = CountrySerializer(many=False, read_only=True)
    country_name = serializers.CharField(write_only=True, max_length=100, required=True)

    class Meta:
        model = UserDeliveryAddress
        fields = ('id', 'country', 'city', 'address', 'phone', 'country_name', 'zip_code')

    def get_country(self, country_name) -> Country:
        country = Country.objects.filter(name=country_name, is_active=True).first()
        if not country:
            raise serializers.ValidationError({'detail': _('Country %s does not support!') % country})
        return country

    def validate(self, attrs):
        attrs['user'] = self.context['request'].user
        country_name = attrs.pop('country_name', None)
        if country_name:
            attrs['country'] = self.get_country(country_name)
        return attrs


class ProductReceiptSerializer(LangSerializerMixin, serializers.ModelSerializer):
    tags = serializers.SlugRelatedField(slug_field='name', read_only=True)

    class Meta:
        model = ProductReceipt
        fields = ('order', 'product', 'tags', 'unit_price', 'purchases_count')
        extra_kwargs = {
            'order': {'write_only': True, 'required': False},
            'unit_price': {'read_only': True},
        }


class OrderSerializer(serializers.ModelSerializer):
    address_id = serializers.IntegerField(write_only=True, required=True)
    delivery_address = DeliveryAddressSerializer(many=False, read_only=True)
    receipts = ProductReceiptSerializer(many=True)

    class Meta:
        model = Order
        fields = ('id', 'status', 'delivery_address', 'receipts', 'address_id')
        extra_kwargs = {'status': {'read_only': True}}

    def get_address(self, address_id):
        address = self.context['request'].user.delivery_addresses.filter(id=address_id).first()
        if not address:
            raise serializers.ValidationError({'detail': _('Invalid address_id!')})
        return address

    def validate(self, attrs):
        address_id = attrs.pop('address_id', None)
        if address_id:
            attrs['delivery_address'] = self.get_address(address_id)
        return attrs

