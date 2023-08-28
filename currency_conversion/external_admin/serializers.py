from rest_framework import serializers

from currency_conversion.models import Conversion


class AdminConversionSerializer(serializers.ModelSerializer):
    CURRENCIES = (
        Conversion.Currencies.dollar,
        Conversion.Currencies.som
    )
    currency = serializers.ChoiceField(choices=CURRENCIES, default='dollar', write_only=True)

    class Meta:
        model = Conversion
        fields = ('id', 'currency_from', 'currency_to', 'price_per', 'currency')
        extra_kwargs = {'currency_from': {'read_only': True}, 'currency_to': {'read_only': True}}

    def validate(self, attrs):
        attrs['currency_to'] = attrs.pop('currency')
        return attrs
