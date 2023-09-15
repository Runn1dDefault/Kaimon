from django.db import models
from django.utils.translation import gettext_lazy as _


class Conversion(models.Model):
    class Currencies(models.TextChoices):
        dollar = 'dollar', _('Dollar')
        som = 'som', _('Som')
        yen = 'yen', _('Yen')

        @classmethod
        def from_string(cls, currency: str):
            match currency:
                case cls.dollar.value:
                    return cls.dollar
                case cls.yen.value:
                    return cls.yen
                case cls.som.value:
                    return cls.som

    currency_from = models.CharField(max_length=10, choices=Currencies.choices, default=Currencies.yen)
    currency_to = models.CharField(max_length=10, choices=Currencies.choices)
    price_per = models.FloatField(help_text=_('unit price currency_from'))
    created_at = models.DateTimeField(auto_now=True)

    def calc_price(self, current_price: float):
        return round(current_price * self.price_per, 2)
