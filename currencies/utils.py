from decimal import Decimal
from functools import lru_cache

from currencies.models import Conversion


@lru_cache(maxsize=3)
def get_currency_price_per(currency: str):
    conversion = Conversion.objects.filter(currency_to=currency).order_by('created_at').first()
    if not conversion:
        return None
    return conversion.price_per


def convert_price(current_price: float | Decimal | int, price_per: Decimal):
    if not isinstance(current_price, Decimal):
        current_price = Decimal(current_price)
    return round(current_price * price_per, 2)
