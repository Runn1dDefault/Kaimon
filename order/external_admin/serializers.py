from django.db.models import F
from django.utils.timezone import localtime
from rest_framework import serializers

from order.models import Order
from order.serializers import ProductReceiptSerializer
from utils.mixins import LangSerializerMixin


class AdminOrderSerializer(LangSerializerMixin, serializers.ModelSerializer):
    email = serializers.SerializerMethodField(read_only=True)
    full_name = serializers.SerializerMethodField(read_only=True)
    total_price = serializers.SerializerMethodField(read_only=True)
    date = serializers.SerializerMethodField(read_only=True)
    country = serializers.SerializerMethodField(read_only=True)
    city = serializers.SerializerMethodField(read_only=True)
    address = serializers.SerializerMethodField(read_only=True)
    phone = serializers.SerializerMethodField(read_only=True)
    zip_code = serializers.SerializerMethodField(read_only=True)
    receipts = ProductReceiptSerializer(many=True, read_only=True)

    class Meta:
        model = Order
        fields = ('id', 'status', 'email', 'full_name', 'total_price', 'date', 'country', 'city', 'phone', 'zip_code',
                  'address', 'receipts')

    def get_email(self, instance):
        return instance.delivery_address.user.email

    def get_full_name(self, instance):
        return instance.delivery_address.user.full_name

    def get_total_price(self, instance):
        receipts = instance.receipts.filter(is_canceled=False, qty__gt=0, unit_price__gt=0)
        return sum(
            receipts.annotate(
                total_price=F('unit_price') * F('qty')
            ).values_list('total_price', flat=True)
        )

    def get_date(self, instance):
        return localtime(instance.created_at).date()

    def get_country(self, instance):
        country = instance.delivery_address.country
        return getattr(country, self.get_translate_field('name')) or country.name

    def get_city(self, instance):
        return instance.delivery_address.city

    def get_address(self, instance):
        return instance.delivery_address.address

    def get_phone(self, instance):
        return instance.delivery_address.phone
