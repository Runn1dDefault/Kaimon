from collections import OrderedDict

from django.conf import settings
from django.core.exceptions import ObjectDoesNotExist
from django.utils import timezone
from django.utils.translation import gettext_lazy as _
from requests import HTTPError
from rest_framework import serializers

from products.models import Product, ProductInventory
from service.clients import fedex
from service.serializers import ConversionField
from service.utils import get_currency_by_id, convert_price

from .models import DeliveryAddress, Order, Receipt, PaymentTransactionReceipt
from .tasks import create_order_payment_transaction
from .utils import duplicate_delivery_address, get_product_yen_price, order_currencies_price_per, create_customer


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


class OrderConversionField(ConversionField):
    def __init__(self, order_id_field: str = "order_id", *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.order_id_field = order_id_field
        self.order_id = None

    def init_instance_currency(self, instance):
        self.instance_currency = instance.site_currency
        self.order_id = getattr(instance, self.order_id_field)

    def convert(self, currency, value):
        if not value or currency == self.instance_currency:
            return value

        price_per = order_currencies_price_per(
            order_id=self.order_id,
            currency_from=self.instance_currency,
            currency_to=currency
        )
        return convert_price(value, price_per) if price_per else None


class ReceiptSerializer(serializers.ModelSerializer):
    inventory_id = serializers.PrimaryKeyRelatedField(
        queryset=ProductInventory.objects.filter(product__is_active=True),
        write_only=True,
        required=True
    )
    unit_price = OrderConversionField(read_only=True)
    total_price = OrderConversionField(read_only=True)
    sale_unit_price = OrderConversionField(read_only=True)

    class Meta:
        model = Receipt
        fields = ('order', 'product_code', 'product_name', 'product_image', 'unit_price', 'total_price',
                  'sale_unit_price', 'discount', 'quantity', 'tags', 'inventory_id')
        extra_kwargs = {
            "product_code": {"read_only": True},
            'order': {'read_only': True},
            'discount': {'read_only': True},
            'product_image': {'read_only': True},
            'product_name': {'read_only': True},
            'tags': {'read_only': True}
        }

    def get_currency(self) -> str:
        return self.context.get('currency', 'yen')

    def validate(self, attrs):
        inventory = attrs.get('inventory_id', None)
        if inventory:
            attrs['unit_price'] = inventory.price
            product = inventory.product
            promotion = product.promotions.active_promotions().first()
            if promotion:
                try:
                    attrs['discount'] = promotion.discount.percentage
                except ObjectDoesNotExist:
                    attrs['discount'] = 0.0

            image = product.images.first()
            attrs['shop_url'] = product.shop_url
            attrs['product_code'] = product.id
            attrs['product_url'] = inventory.product_url
            if inventory.id.startswith('uniqlo'):
                attrs['product_name'] = product.name
            else:
                attrs['product_name'] = inventory.name
            attrs['product_image'] = image.url if image else None
            attrs['site_currency'] = get_currency_by_id(product.id)
            attrs['site_price'] = inventory.site_price
            attrs['tags'] = ', '.join(inventory.tags.values_list('name', flat=True))
        return attrs

    def create(self, validated_data):
        inventory = validated_data.pop('inventory_id')
        receipt = super().create(validated_data)
        receipt.tags.add(*list(inventory.tags.values_list('id', flat=True)))
        return receipt


class PaymentTransactionSerializer(serializers.ModelSerializer):
    class Meta:
        model = PaymentTransactionReceipt
        fields = ("order", "send_amount", "redirect_url")
        read_only_fields = ("order", "send_amount", "redirect_url")


class OrderSerializer(serializers.ModelSerializer):
    address_id = serializers.PrimaryKeyRelatedField(
        queryset=DeliveryAddress.objects.all(),
        write_only=True,
        required=True
    )
    delivery_address = DeliveryAddressSerializer(many=False, read_only=True)
    receipts = ReceiptSerializer(many=True, required=True)

    class Meta:
        model = Order
        fields = ('id', 'status', 'delivery_address', 'receipts', 'address_id', 'comment',
                  'created_at')
        extra_kwargs = {'status': {'read_only': True}}

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._transaction_data = None

    def validate(self, attrs):
        address = attrs.get('address_id')
        if address and not self.context['request'].user.delivery_addresses.filter(id=address.id).exists():
            raise serializers.ValidationError(
                {'address_id': _("Invalid pk \"%s\" - object does not exist.") % address.id}
            )
        return attrs

    def create(self, validated_data):
        user = self.context['request'].user
        validated_data['customer'] = create_customer(user)
        validated_data['delivery_address'] = validated_data.pop('address_id')

        products_data = validated_data.pop('receipts')
        order = super().create(validated_data)
        receipts = []
        for product_data in products_data:
            product_data['order'] = order
            product_data.pop('inventory_id')
            receipts.append(Receipt(**product_data))

        if receipts:
            Receipt.objects.bulk_create(receipts)
            create_order_payment_transaction.delay(order.id)
        return order


class ProductQuantitySerializer(serializers.Serializer):
    product = serializers.PrimaryKeyRelatedField(
        queryset=Product.objects.filter(is_active=True),
        write_only=True,
        required=True
    )
    quantity = serializers.IntegerField(write_only=True, default=1)
    width = serializers.IntegerField(write_only=True, required=True)
    length = serializers.IntegerField(write_only=True, required=True)
    height = serializers.IntegerField(write_only=True, required=True)


class FedexQuoteRateSerializer(serializers.Serializer):
    country_code = serializers.ChoiceField(
        choices=DeliveryAddress.CountryCode.choices,
        required=True,
        write_only=True
    )
    postal_code = serializers.CharField(required=False, write_only=True)
    city = serializers.CharField(required=False, write_only=True)
    products = ProductQuantitySerializer(many=True, write_only=True, required=True)

    def validate(self, attrs):
        try:
            country_code = attrs['country_code']
            postal_code = attrs.get('postal_code') or "0000"
            city = attrs.get("city")

            commodities = []
            package_line_items = []
            for data in attrs['products']:
                product = data['product']
                category = product.categories.filter(avg_weight__isnull=False).first()
                avg_weight = settings.FEDEX_DEFAULT_AVG_WEIGHT
                if category and category.avg_weight > 0:
                    avg_weight = category.avg_weight

                quantity = data['quantity']
                width, length, height = data['width'], data['length'], data['height']
                commodities.append(
                    fedex.FedexCommodity(
                        weight=fedex.FedexWeight(units="KG", value=avg_weight),
                        currency_amount=fedex.FedexCurrencyAmount(
                            currency='JYE',
                            amount=float(get_product_yen_price(product, quantity))
                        ),
                        quantity=quantity
                    )
                )
                package_line_items.append(
                    fedex.FedexRequestedPackageLineItem(
                        weight=fedex.FedexWeight(units="KG", value=avg_weight),
                        dimensions=fedex.FedexDimension(width=width, length=length, height=height)
                    )
                )

            client = fedex.FedexAPIClient(
                client_id=settings.FEDEX_CLIENT_ID,
                client_secret=settings.FEDEX_SECRET,
                account_number=settings.FEDEX_ACCOUNT_NUMBER
            )
            fedex_response = client.international_rate_quotes(
                shipper=fedex.FedexAddress(
                    postal_code=settings.SHIPPER_POSTAL_CODE,
                    country_code=settings.SHIPPER_COUNTRY_CODE,
                    residential=False
                ),
                recipient=fedex.FedexAddress(
                    postal_code=postal_code,
                    country_code=country_code,
                    city=city,
                    residential=False
                ),
                commodities=commodities,
                package_line_items=package_line_items,
                ship_date=timezone.localtime(timezone.now()).date()
            )
        except HTTPError as http_exc:
            error_data = http_exc.response.json()
            raise serializers.ValidationError({'detail': error_data['errors']})
        else:
            return fedex_response['output']

    def to_representation(self, validated_data):
        data = OrderedDict()
        rate_details = validated_data['rateReplyDetails'][0]
        data['service_name'] = rate_details['serviceName']
        data['arrives_on'] = rate_details['commit']['dateDetail']['dayFormat']
        data['shipment_details'] = [
            {
                "base_rate": rate['totalBaseCharge'],
                "currency": rate['currency'],
                "surcharges": [
                    {"name": surcharge['description'], "amount": surcharge["amount"]}
                    for surcharge in rate.get('shipmentRateDetail', {}).get('surCharges') or []
                ],
                "discounts": [
                    {"name": discount['description'], "amount": discount['amount']}
                    for discount in rate.get('shipmentRateDetail', {}).get('freightDiscount') or []
                ],
                "total_estimate": rate['totalNetCharge']
            }
            for rate in rate_details['ratedShipmentDetails']
        ]
        return data
