import uuid
from datetime import datetime
from decimal import Decimal
from functools import lru_cache

import qrcode

from .enums import Site, SiteCurrency
from .models import Conversion, Currencies


def import_model(model_import_path: str):
    assert '.' in model_import_path

    package = model_import_path.split('.')
    model_name = package[-1]
    mod = __import__('.'.join(package[:-1]), fromlist=[model_name])
    return getattr(mod, model_name)


def increase_price(price, percentage):
    if percentage > 0:
        price = Decimal(price)
        return price + (Decimal(percentage) * price / 100)
    return price


def round_half_integer(number):
    integer_part = int(number)
    decimal_part = number - integer_part

    if decimal_part < 0.3:
        rounded_decimal_part = 0
    elif decimal_part < 0.6:
        rounded_decimal_part = 0.5
    else:
        rounded_decimal_part = 1.0

    return integer_part + rounded_decimal_part


def convert_date(date_string: str):
    return datetime.strptime(date_string, "%Y-%m-%d").date()


def uid_generate(prefix: str = 'kaimono'):
    return prefix + '_' + str(uuid.uuid4())


def recursive_single_tree(current, related_field: str) -> list[int]:
    """
    recursive way to get all ancestors including the genre itself
    It is important to remember that with this approach we work from the bottom up.
     And we get a list from the category itself to the topmost parent
    """
    collected_parents = []
    relation_fk = getattr(current, related_field)
    if relation_fk is None:
        return collected_parents
    else:
        collected_parents.append(relation_fk.id)
        collected_parents.extend(recursive_single_tree(relation_fk, related_field))
    return collected_parents


def recursive_many_tree(current, related_field: str) -> list[int]:
    """
    recursive way to get children that are missing children
    """
    last_children = []

    for child in getattr(current, related_field).all():
        if not getattr(child, related_field).exists():
            last_children.append(child.id)
            continue

        last_children.extend(recursive_many_tree(child, related_field))
    return last_children


def get_site_from_id(obj_id: str) -> str:
    return obj_id.split('_')[0]


@lru_cache(maxsize=4)
def get_currencies_price_per(currency_from, currency_to) -> Decimal | None:
    if currency_from == currency_to:
        return None

    conversion = Conversion.objects.filter(currency_from=currency_from, currency_to=currency_to).first()
    if conversion:
        return conversion.price_per


def convert_price(current_price: float | Decimal | int, price_per: Decimal):
    if not isinstance(current_price, Decimal):
        current_price = Decimal(current_price)
    return current_price * price_per


def get_currency_by_id(instance_id):
    site = Site.from_instance_id(instance_id)
    return Currencies.from_string(SiteCurrency.from_string(site).value)


def generate_qrcode(filepath: str, url: str):
    qr = qrcode.QRCode(version=1, error_correction=qrcode.constants.ERROR_CORRECT_L, box_size=10,
                       border=4)
    qr.add_data(url)
    qr.make(fit=True)
    img = qr.make_image(fill_color="black", back_color="white")
    img.save(filepath)