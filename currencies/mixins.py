from django.conf import settings


class CurrencyMixin:
    def get_currency(self):
        return self.request.query_params.get(settings.CURRENCY_QUERY_PARAM, 'yen')

    def get_serializer_context(self):
        context = super().get_serializer_context()
        context.setdefault('currency', self.get_currency())
        return context
