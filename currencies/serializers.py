from rest_framework import serializers

from .models import Conversion
from .utils import get_currency_price_per, convert_price


class ConversionField(serializers.FloatField):
    def __init__(self, all_conversions=False, **kwargs):
        self.all_conversions = all_conversions
        super().__init__(**kwargs)

    def get_currency(self):
        return Conversion.Currencies.from_string(self.context.get('currency', 'yen'))

    def to_representation(self, value):
        value = super().to_representation(value)
        if self.all_conversions:
            som = get_currency_price_per(Conversion.Currencies.som)
            dollar = get_currency_price_per(Conversion.Currencies.dollar)
            return {
                Conversion.Currencies.yen: value,
                Conversion.Currencies.som: convert_price(value, som) if som else None,
                Conversion.Currencies.dollar: convert_price(value, dollar) if dollar else None
            }

        currency = self.get_currency()
        if currency == Conversion.Currencies.yen or not value:
            return value

        price_per = get_currency_price_per(currency)
        return convert_price(value, price_per) if price_per else None
