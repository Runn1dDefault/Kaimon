import logging
from collections import OrderedDict

from django.core.exceptions import ObjectDoesNotExist
from django.utils.translation import gettext_lazy as _
from requests import HTTPError
from rest_framework import serializers

from currencies.models import Conversion
from currencies.utils import get_currency_price_per
from product.models import Product, Tag

from .models import DeliveryAddress, Order, Receipt, Customer, ReceiptTag
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
    tags = serializers.SerializerMethodField(read_only=True)
    product_id = serializers.PrimaryKeyRelatedField(
        queryset=Product.objects.filter(is_active=True, availability=True),
        write_only=True,
        required=True
    )
    tag_ids = serializers.PrimaryKeyRelatedField(
        queryset=Tag.objects.all(),
        write_only=True,
        required=False,
        many=True
    )
    product_name = serializers.SerializerMethodField(read_only=True)
    product_image = serializers.SerializerMethodField(read_only=True)
    unit_price = serializers.SerializerMethodField(read_only=True)

    class Meta:
        model = Receipt
        fields = ('order', 'product_id', 'product_name', 'product_image', 'unit_price', 'discount', 'quantity', 'tags',
                  'tag_ids',)
        extra_kwargs = {'order': {'read_only': True}, 'unit_price': {'read_only': True},
                        'discount': {'read_only': True}}

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

    def get_unit_price(self, instance):
        currency = self.get_currency()
        match currency:
            case 'dollar':
                return instance.unit_price * instance.order.yen_to_usd
            case 'som':
                return instance.unit_price * instance.order.yen_to_som
        return instance.unit_price

    def get_product_name(self, instance):
        return instance.product.name

    def get_product_image(self, instance):
        if instance.product.image_urls.exists():
            return instance.product.image_urls.first().url

    def get_tags(self, instance):
        return list(instance.tags.values_list('tag__name', flat=True))

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
        queryset=DeliveryAddress.objects.filter(as_deleted=False),
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

        dollar = get_currency_price_per(Conversion.Currencies.dollar)
        som = get_currency_price_per(Conversion.Currencies.som)
        if not dollar or not som:
            logging.warning('no entries were found for conversion')

        attrs['yen_to_usd'] = dollar
        attrs['yen_to_som'] = som
        return attrs

    def create(self, validated_data):
        phone = validated_data.pop('phone')
        user = self.context['request'].user
        customer, _ = Customer.objects.get_or_create(
            name=user.full_name,
            email=user.email,
            phone=phone
        )
        validated_data['customer'] = customer
        address = validated_data.pop('address_id')
        validated_data['delivery_address'] = address
        receipts_data = validated_data.pop('products')
        order = super().create(validated_data)
        receipts = []
        receipt_tags = []

        for product_data in receipts_data:
            product = product_data['product_id']
            receipt = Receipt(
                order=order,
                product=product,
                unit_price=product.price,
                discount=product.discount.percentage if getattr(product, 'discount', None) else 0.0,
                quantity=product_data['quantity']
            )
            receipts.append(receipt)

            tags = product_data.get('tag_ids')
            if tags:
                receipt_tags.extend([ReceiptTag(receipt=receipt, tag=tag) for tag in tags])

        if receipts:
            Receipt.objects.bulk_create(receipts)
        if receipt_tags:
            ReceiptTag.objects.bulk_create(receipt_tags)
        return order

    def update(self, instance, validated_data):
        comment = validated_data.get('comment', None)
        if comment:
            instance.comment = comment
            instance.save()

        phone = validated_data.pop('phone', None)
        if phone != instance.customer.phone:
            instance.customer.phone = phone
            instance.customer.save()

        if not validated_data:
            return instance

        if instance.status != Order.Status.pending:
            raise serializers.ValidationError({'detail': _("not available for update")})

        receipts = validated_data.pop('products', [])

        for receipt in receipts:
            receipt_id = receipt.pop('id', None)
            if not receipt_id:
                raise serializers.ValidationError({"products": [{"id": _("required")}]})

            receipt_obj = instance.receipts.filter(id=receipt_id).first()
            if not receipt_obj:
                raise serializers.ValidationError(
                    {'products': [{"id": _("Invalid pk \"%s\" - object does not exist.")}]}
                )

            save = False
            for key, value in receipt.items():
                if hasattr(receipt_obj, key) and value != getattr(receipt_obj, key):
                    setattr(receipt_obj, key, value)
                    save = True

            if save:
                receipt.save()
        return instance

    def get_total_price(self, instance):
        if not instance.receipts.exists():
            return 0.0

        currency = self.context.get('currency', 'yen')
        return instance.total_prices.get(currency) or instance.total_prices['yen']


class ProductQuantitySerializer(serializers.Serializer):
    product = serializers.PrimaryKeyRelatedField(
        queryset=Product.objects.filter(is_active=True, availability=True),
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
