import logging

from django.core.exceptions import ObjectDoesNotExist
from django.utils.translation import gettext_lazy as _
from rest_framework import serializers

from currencies.models import Conversion
from product.models import Product, Tag
from utils.serializers import LangSerializerMixin

from .models import DeliveryAddress, Order, Receipt, Customer, ReceiptTag
from .utils import duplicate_delivery_address
from .validators import only_digit_validator


class DeliveryAddressSerializer(serializers.ModelSerializer):
    class Meta:
        model = DeliveryAddress
        fields = ('id', 'recipient_name', 'country', 'city', 'state', 'address_line', 'postal_code')

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


class ReceiptSerializer(LangSerializerMixin, serializers.ModelSerializer):
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

    class Meta:
        model = Receipt
        fields = ('order', 'product_id', 'unit_price', 'discount', 'quantity', 'tags', 'tag_ids',)
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

    def get_tags(self, instance):
        field = self.get_translate_field('tag__name')
        return list(instance.tags.values_list(field, flat=True))

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

    class Meta:
        model = Order
        fields = ('id', 'status', 'delivery_address', 'receipts', 'products', 'address_id', 'phone', 'comment')
        extra_kwargs = {'status': {'read_only': True}}

    def validate(self, attrs):
        address = attrs.get('address_id')
        if address and not self.context['request'].user.delivery_addresses.filter(id=address.id).exists():
            raise serializers.ValidationError(
                {'address_id': _("Invalid pk \"%s\" - object does not exist.") % address.id}
            )

        dollar_conversion = Conversion.objects.filter(
            currency_from=Conversion.Currencies.yen,
            currency_to=Conversion.Currencies.dollar
        ).first()
        som_conversion = Conversion.objects.filter(
            currency_from=Conversion.Currencies.yen,
            currency_to=Conversion.Currencies.som
        ).first()
        if not dollar_conversion or not som_conversion:
            logging.warning('no entries were found for conversion')

        attrs['yen_to_usd'] = dollar_conversion.price_per if dollar_conversion else 0.0
        attrs['yen_to_som'] = som_conversion.price_per if som_conversion else 0.0
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
