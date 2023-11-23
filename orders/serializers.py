import logging
from collections import OrderedDict

from django.core.exceptions import ObjectDoesNotExist
from django.utils.translation import gettext_lazy as _
from requests import HTTPError
from rest_framework import serializers

from products.models import Product, Tag
from service.models import Currencies
from service.serializers import ConversionField
from service.utils import get_currencies_price_per, get_currency_by_id, convert_price

from .models import DeliveryAddress, Order, Receipt, Customer
from .utils import duplicate_delivery_address, fedex_international_quotes
from .validators import only_digit_validator


class DeliveryAddressSerializer(serializers.ModelSerializer):
    class Meta:
        model = DeliveryAddress
        fields = ('id', 'recipient_name', 'country_code', 'city', 'address_line', 'postal_code')

    def validate(self, attrs):
        attrs['user'] = self.context['request'].user
        return attrs

    def update(self, instance, validated_data):
        if instance.orders.exists():
            # for any updates, the old data must be preserved if the address had orders
            duplicated_address = duplicate_delivery_address(instance, updates=validated_data)
            instance.as_deleted = True
            instance.save()
            return duplicated_address
        return super().update(instance, validated_data)


class ReceiptSerializer(serializers.ModelSerializer):
    tags = serializers.SlugRelatedField(slug_field='name', read_only=True)
    product_id = serializers.PrimaryKeyRelatedField(
        queryset=Product.objects.filter(is_active=True),
        write_only=True,
        required=True
    )
    tag_ids = serializers.PrimaryKeyRelatedField(
        queryset=Tag.objects.all(),
        write_only=True,
        required=False,
        many=True
    )
    unit_price = ConversionField(read_only=True)

    class Meta:
        model = Receipt
        fields = ('order', 'product_id', 'product_name', 'product_image', 'unit_price', 'discount', 'quantity', 'tags',
                  'tag_ids',)
        extra_kwargs = {
            'order': {'read_only': True},
            'discount': {'read_only': True},
            'product_image': {'read_only': True}
        }

    def validate(self, attrs):
        tags = attrs.get('tag_ids')
        product = attrs['product_id']
        for tag in tags or []:
            if not product.tags.filter(tag_id=tag.id).exists():
                raise serializers.ValidationError(
                    {'tag_ids': _("Invalid pk \"%s\" - object does not exist.") % tag.id}
                )
        return attrs

    def get_currency(self) -> str:
        return self.context.get('currency', 'yen')

    def create(self, validated_data):
        product = validated_data['product_id']
        validated_data['unit_price'] = product.price
        try:
            validated_data['discount'] = product.discount.percentage
        except ObjectDoesNotExist:
            validated_data['discount'] = 0.0
        return super().create(validated_data)


class OrderSerializer(serializers.ModelSerializer):
    phone = serializers.CharField(
        max_length=13,
        required=True,
        validators=[only_digit_validator]
    )
    address_id = serializers.PrimaryKeyRelatedField(
        queryset=DeliveryAddress.objects.all(),
        write_only=True,
        required=True
    )
    delivery_address = DeliveryAddressSerializer(many=False, read_only=True)
    receipts = ReceiptSerializer(many=True, read_only=True)
    products = ReceiptSerializer(many=True, write_only=True, required=True)
    total_price = serializers.SerializerMethodField(read_only=True)

    class Meta:
        model = Order
        fields = ('id', 'status', 'delivery_address', 'receipts', 'products', 'address_id', 'phone', 'comment',
                  'created_at', 'total_price')
        extra_kwargs = {'status': {'read_only': True}}

    def validate(self, attrs):
        address = attrs.get('address_id')
        if address and not self.context['request'].user.delivery_addresses.filter(id=address.id).exists():
            raise serializers.ValidationError(
                {'address_id': _("Invalid pk \"%s\" - object does not exist.") % address.id}
            )
        return attrs

    @staticmethod
    def create_customer(user, phone):
        customer, _ = Customer.objects.get_or_create(
            name=user.full_name,
            email=user.email,
            phone=phone
        )
        return customer

    def create(self, validated_data):
        user = self.context['request'].user

        validated_data['customer'] = self.create_customer(user, validated_data.pop('phone'))
        validated_data['delivery_address'] = validated_data.pop('address_id')
        products_data = validated_data.pop('products')

        order = super().create(validated_data)

        receipts = []
        collected_tags = {}
        main_currency = Currencies.main_currency()
        for product_data in products_data:
            product = product_data['product_id']
            product_currency = get_currency_by_id(product.id)

            price, site_price = product.price, product.site_price
            if product_currency != main_currency:
                price_per = get_currencies_price_per(main_currency, product_currency)
                price = convert_price(price, price_per)
                site_price = convert_price(site_price, price_per)

            image = product.images.first()
            category = product.categories.filter(
                avg_weight__isnull=False
            ).order_by('level').first()
            avg_weight = 0 if not category else category.avg_weight
            receipt = Receipt(
                order=order,
                product=product,
                product_name=product.name,
                product_image=image.url if image else None,
                quantity=product_data['quantity'],
                unit_price=price,
                site_price=site_price,
                avg_weight=avg_weight,
                discount=product.discount.percentage if getattr(product, 'discount', None) else 0.0,
            )
            receipts.append(receipt)

            tags = product_data.get('tag_ids')
            if tags:
                collected_tags[product.id] = tags

        if receipts:
            for receipt in Receipt.objects.bulk_create(receipts):
                product_id = getattr(receipt, 'product_id')
                tags = collected_tags.get(product_id)
                if tags:
                    receipt.tags.add(*tags)
        return order

    def get_total_price(self, instance):
        if not instance.receipts.exists():
            return 0.0

        currency = self.context.get('currency', 'yen')
        return instance.total_prices.get(currency) or instance.total_prices['yen']


class ProductQuantitySerializer(serializers.Serializer):
    product = serializers.PrimaryKeyRelatedField(
        queryset=Product.objects.filter(is_active=True),
        write_only=True,
        required=True
    )
    quantity = serializers.IntegerField(write_only=True, default=1)


class FedexQuoteRateSerializer(serializers.Serializer):
    country_code = serializers.ChoiceField(
        choices=DeliveryAddress.CountryCode.choices,
        required=True,
        write_only=True
    )
    postal_code = serializers.CharField(required=False, write_only=True)
    products = ProductQuantitySerializer(many=True, write_only=True, required=True)

    def validate(self, attrs):
        try:
            fedex_response = fedex_international_quotes(
                products_with_count=attrs['products'],
                country_code=attrs['country_code'],
                postal_code=attrs.get('postal_code') or "00000"
            )
        except HTTPError as http_err:
            logging.error(http_err)
            # TODO: handling errors on prod
            raise serializers.ValidationError({'detail': "Something went wrong!"})
        else:
            return fedex_response['output']

    def to_representation(self, validated_data):
        rate_details = validated_data['rateReplyDetails']
        international_details = [i for i in rate_details if i['serviceType'] == 'INTERNATIONAL_PRIORITY']
        service_detail = international_details[0] if international_details else rate_details[0]
        shipment_data = service_detail['ratedShipmentDetails'][0]

        data = OrderedDict()
        # data['quote_date'] = validated_data['quoteDate']
        data['base_rate'] = shipment_data['totalBaseCharge']
        data['surcharges'] = [
            {"title": sur["description"], "amount": sur['amount']}
            for sur in shipment_data['shipmentRateDetail'].get('surCharges') or []
        ]
        data['fees_and_taxes_details'] = [
            {"title": fees["description"], "amount": fees['amount']}
            for fees in shipment_data['ancillaryFeesAndTaxes']
        ]
        data['fees_and_taxes'] = shipment_data['totalAncillaryFeesAndTaxes']
        data['total_estimate'] = shipment_data['totalNetChargeWithDutiesAndTaxes']
        return data
