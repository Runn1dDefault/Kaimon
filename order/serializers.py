from django.db import transaction
from django.utils.translation import gettext_lazy
from rest_framework import serializers

from currencies.models import Conversion
from product.models import Product, Tag
from utils.mixins import LangSerializerMixin

from .models import DeliveryAddress, Order, OrderReceipt, Customer
from .utils import duplicate_delivery_address
from .validators import only_digit_validator


class DeliveryAddressSerializer(serializers.ModelSerializer):
    class Meta:
        model = DeliveryAddress
        fields = ('id', 'recipient_name', 'address_line1', 'address_line2', 'city', 'state', 'postal_code', 'country')

    def validate(self, attrs):
        attrs['user'] = self.context['request'].user
        return attrs

    def update(self, instance, validated_data):
        if instance.orders.exists():
            duplicated_address = duplicate_delivery_address(instance, updates=validated_data)
            instance.as_deleted = True
            instance.save()
            return duplicated_address
        return super().update(instance, validated_data)


class OrderReceiptSerializer(LangSerializerMixin, serializers.ModelSerializer):
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
        model = OrderReceipt
        fields = ('order', 'product_id', 'unit_price', 'discount', 'quantity', 'tags', 'tag_ids',)
        extra_kwargs = {'order': {'read_only': True}, 'unit_price': {'read_only': True},
                        'discount': {'read_only': True}}

    def validate(self, attrs):
        tags = attrs.get('tag_ids')
        if tags:
            product = attrs['product_id']
            for tag in tags:
                if not product.tags.filter(id=tag.id).exists():
                    raise serializers.ValidationError(
                        {'tag_ids': gettext_lazy("Invalid pk \"%s\" - object does not exist.") % tag.id}
                    )
        return attrs

    def get_tags(self, instance):
        lang = self.get_lang()
        field = 'name' if lang == 'ja' else 'name_' + lang
        return list(instance.tags.values_list(field, flat=True))


class OrderSerializer(serializers.ModelSerializer):
    phone = serializers.CharField(max_length=13, write_only=True, required=True, validators=[only_digit_validator])
    address_id = serializers.PrimaryKeyRelatedField(
        queryset=DeliveryAddress.objects.filter(as_deleted=False),
        write_only=True,
        required=True
    )
    delivery_address = DeliveryAddressSerializer(many=False, read_only=True)
    receipts = OrderReceiptSerializer(many=True, read_only=True)
    products = OrderReceiptSerializer(many=True, write_only=True, required=True)

    class Meta:
        model = Order
        fields = ('id', 'status', 'delivery_address', 'receipts', 'products', 'address_id', 'phone', 'comment')
        extra_kwargs = {'status': {'read_only': True}}

    def validate(self, attrs):
        address = attrs.get('address_id')
        if address and not self.context['request'].user.delivery_addresses.filter(id=address.id).exists():
            raise serializers.ValidationError(
                {'address_id': gettext_lazy("Invalid pk \"%s\" - object does not exist.") % address.id}
            )
        return attrs

    def create(self, validated_data):
        dollar_conversion = Conversion.objects.filter(
            currency_from=Conversion.Currencies.yen,
            currency_to=Conversion.Currencies.dollar
        ).first()
        if not dollar_conversion:
            raise serializers.ValidationError({'detail': gettext_lazy('Not found dollar conversion')})

        som_conversion = Conversion.objects.filter(
            currency_from=Conversion.Currencies.yen,
            currency_to=Conversion.Currencies.som
        ).first()
        if not som_conversion:
            raise serializers.ValidationError({'detail': gettext_lazy('Not found som conversion')})

        validated_data['yen_to_usd'] = dollar_conversion.price_per
        validated_data['yen_to_som'] = som_conversion.price_per

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

        with transaction.atomic():
            order = super().create(validated_data)
            order_receipts = []
            collected_product_tags = {}

            for product_data in receipts_data:
                product = product_data['product_id']
                tags = product_data.get('tag_ids')

                if tags and product.id not in collected_product_tags.keys():
                    collected_product_tags[product.id] = []

                if tags:
                    collected_product_tags[product.id].extend(tags)

                receipt = OrderReceipt(
                    order=order,
                    product=product,
                    unit_price=product.price,
                    discount=product.discount.percentage if getattr(product, 'discount', None) else 0.0,
                    quantity=product_data['quantity']
                )
                order_receipts.append(receipt)

            receipts = OrderReceipt.objects.bulk_create(order_receipts)
            for receipt in receipts:
                tags = collected_product_tags.get(receipt.product.id)
                if tags:
                    receipt.tags.add(*tags)
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
            raise serializers.ValidationError({'detail': gettext_lazy("not available for update")})

        receipts = validated_data.pop('products', [])

        for receipt in receipts:
            receipt_id = receipt.pop('id', None)
            if not receipt_id:
                raise serializers.ValidationError(
                    {"products": [{"id": gettext_lazy("required")}]}
                )

            receipt_obj = instance.receipts.filter(id=receipt_id).first()
            if not receipt_obj:
                raise serializers.ValidationError(
                    {'products': [{"id": gettext_lazy("Invalid pk \"%s\" - object does not exist.")}]}
                )

            save = False
            for key, value in receipt.items():
                if hasattr(receipt_obj, key) and value != getattr(receipt_obj, key):
                    setattr(receipt_obj, key, value)
                    save = True

            if save:
                receipt.save()
        return instance
