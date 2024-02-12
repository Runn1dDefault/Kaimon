from decimal import Decimal

from django.db import models
from django.utils.translation import gettext_lazy as _


class Currencies(models.TextChoices):
    usd = 'usd', _('Dollar')
    som = 'som', _('Som')
    yen = 'yen', _('Yen')
    moneta = 'moneta', _('Moneta')

    @classmethod
    def from_string(cls, currency: str):
        match currency:
            case cls.usd.value:
                return cls.usd
            case cls.yen.value:
                return cls.yen
            case cls.som.value:
                return cls.som
            case cls.moneta.value:
                return cls.moneta

    @classmethod
    def to_symbol(cls, currency: str) -> str:
        currency_symbols = {cls.usd.value: "$", cls.som.value: "С", cls.yen.value: "¥"}
        return currency_symbols.get(currency, "")

    @classmethod
    def main_currency(cls):
        return cls.yen


class Conversion(models.Model):
    objects = models.Manager()

    currency_from = models.CharField(max_length=10, choices=Currencies.choices, default=Currencies.yen)
    currency_to = models.CharField(max_length=10, choices=Currencies.choices)
    price_per = models.DecimalField(max_digits=20, decimal_places=10, help_text=_('unit price currency_from'))
    created_at = models.DateTimeField(auto_now=True)

    def calc_price(self, current_price: Decimal):
        if not isinstance(current_price, Decimal):
            current_price = Decimal(current_price)
        return round(current_price * self.price_per, 2)
