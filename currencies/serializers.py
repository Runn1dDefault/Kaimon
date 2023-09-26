from rest_framework import serializers

from .models import Conversion


class ConversionField(serializers.FloatField):
    def __init__(self, all_conversions=False, **kwargs):
        self.all_conversions = all_conversions
        super().__init__(**kwargs)

    @staticmethod
    def get_conversation_instance(currency: str) -> Conversion | None:
        return Conversion.objects.filter(currency_to=currency).order_by('created_at').first()

    def get_currency(self):
        return Conversion.Currencies.from_string(self.context.get('currency', 'yen'))

    def get_convert_fields(self) -> list[str]:
        return getattr(self.Meta, 'currency_convert_fields', [])

    def to_representation(self, value):
        value = super().to_representation(value)
        if self.all_conversions:
            som_conversion = self.get_conversation_instance(Conversion.Currencies.som)
            dollar_conversion = self.get_conversation_instance(Conversion.Currencies.dollar)
            if som_conversion and dollar_conversion:
                return {
                    Conversion.Currencies.yen: value,
                    Conversion.Currencies.som: som_conversion.calc_price(value),
                    Conversion.Currencies.dollar: dollar_conversion.calc_price(value)
                }

        currency = self.get_currency()
        if currency == Conversion.Currencies.yen or not value:
            return value

        conversation_instance = self.get_conversation_instance(currency)
        if not conversation_instance:
            return None
        return conversation_instance.calc_price(value)
