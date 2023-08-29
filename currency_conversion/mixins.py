from django.conf import settings

from .models import Conversion


class CurrencyMixin:
    def get_currency(self):
        return self.request.query_params.get(settings.CURRENCY_QUERY_PARAM, 'yen')

    def get_serializer_context(self):
        context = super().get_serializer_context()
        context['currency'] = self.get_currency()
        return context


class CurrencySerializerMixin:
    def get_currency(self) -> str:
        return self.context.get('currency', 'yen')

    def get_conversation_instance(self) -> Conversion | None:
        return Conversion.objects.filter(currency_to=self.get_currency()).order_by('created_at').first()

    def get_convert_fields(self) -> list[str]:
        meta = getattr(self, 'Meta', None)
        return getattr(meta, 'currency_convert_fields', [])

    def get_converted_price(self, price):
        conversation_instance = self.get_conversation_instance()
        if not conversation_instance:
            return None
        return conversation_instance.calc_price(price)

    def to_representation(self, instance):
        representation = super().to_representation(instance)
        for field in self.get_convert_fields():
            value = representation.get(field, None)
            if not value or self.get_currency() == 'yen':
                continue
            representation[field] = self.get_converted_price(value)
        return representation
