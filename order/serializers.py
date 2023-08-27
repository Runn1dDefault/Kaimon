from django.db import transaction
from django.utils.translation import gettext_lazy as _
from rest_framework import serializers

from product.models import Product
from utils.mixins import LangSerializerMixin

from .models import Order, UserDeliveryAddress, Country, ProductReceipt


class CountrySerializer(serializers.ModelSerializer, LangSerializerMixin):
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


class ProductReceiptSerializer(serializers.ModelSerializer, LangSerializerMixin):
    total_price = serializers.SerializerMethodField(read_only=True)
    qty = serializers.IntegerField(required=True)

    class Meta:
        model = ProductReceipt
        fields = ('order', 'p_id', 'product_name', 'image_url', 'unit_price', 'total_price', 'qty', 'returns')
        extra_kwargs = {
            'order': {'write_only': True, 'required': False},
            'product_name': {'read_only': True},
            'image_url': {'read_only': True},
            'unit_price': {'read_only': True},
            'returns': {'read_only': True}
        }

    def get_total_price(self, instance):
        if instance.qty == 0:
            return 0
        return instance.qty * instance.unit_price

    def get_product(self, product_id):
        product = Product.objects.filter(id=product_id, is_active=True).first()
        if not product:
            raise serializers.ValidationError({'detail': _('Product with id %s not found!') % product_id})
        return product

    def validate_product_qty(self, qty, product):
        if qty > product.count:
            msg_params = (qty, product.id, product.count)
            raise serializers.ValidationError(
                {'detail': _('Invalid quantity %s for product %s max quantity is %s') % msg_params}
            )

    def create(self, validated_data):
        product_id = validated_data['p_id']
        product = self.get_product(product_id)
        self.validate_product_qty(qty=validated_data['qty'], product=product)
        validated_data['product'] = product
        validated_data['image_url'] = product.image_url
        validated_data['unit_price'] = product.price
        validated_data['product_name'] = getattr(product, self.get_translate_field('name'), product.name)
        return super().create(validated_data)

    def update(self, instance, validated_data):
        product_id = validated_data['p_id']
        product = self.get_product(product_id)
        qty = validated_data['qty']
        self.validate_product_qty(qty, product)
        if qty < instance.qty:
            validated_data['returns'] = instance.qty - qty
        elif qty == instance.qty:
            validated_data['returns'] = instance.qty
        return super().update(instance, validated_data)


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

    def create(self, validated_data):
        receipts = validated_data.pop('receipts', None)
        if not receipts:
            raise serializers.ValidationError({'detail': _('receipts is required!')})
        with transaction.atomic():
            order = super().create(validated_data)
            for receipt in receipts:
                receipt['order'] = order.id
                serializer = ProductReceiptSerializer(data=receipt, many=False, context=self.context)
                serializer.is_valid(raise_exception=True)
                serializer.save()
        return order

    def update(self, instance, validated_data):
        receipts = validated_data.pop('receipts', None)
        with transaction.atomic():
            for receipt in receipts or []:
                receipt_id = receipt['p_id']
                receipt_instance = ProductReceipt.objects.filter(order=instance, p_id=receipt_id).first()
                if not receipt_instance:
                    raise serializers.ValidationError({'detail': _('Not found receipt with id %s') % receipt_id})

                serializer = ProductReceiptSerializer(
                    instance=receipt_instance,
                    data=receipt,
                    many=False,
                    context=self.context,
                    partial=True
                )
                serializer.is_valid(raise_exception=True)
                serializer.save()
            updated = super().update(instance, validated_data)
        return updated
