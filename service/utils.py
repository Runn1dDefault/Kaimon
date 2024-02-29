import json
import unicodedata
import uuid
import time
from datetime import datetime
from decimal import Decimal
from functools import lru_cache, wraps

import qrcode
import requests
from django.db import connection, reset_queries


from .enums import Site, SiteCurrency
from .models import Conversion, Currencies


def query_debugger(func):
    @wraps(func)
    def inner_func(*args, **kwargs):
        reset_queries()

        start_queries = len(connection.queries)

        start = time.perf_counter()
        result = func(*args, **kwargs)
        end = time.perf_counter()

        end_queries = len(connection.queries)

        print(f"Function : {func.__name__}")
        print(f"Number of Queries : {end_queries - start_queries}")
        print(f"Finished in : {(end - start):.2f}s")
        return result

    return inner_func


def check_to_json(instance, key):
    data = instance.get(key, {})
    if isinstance(data, str):
        data = json.loads(data)
    return data


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


@lru_cache(maxsize=9)
def get_currencies_price_per(currency_from, currency_to) -> Decimal | None:
    if currency_from == currency_to:
        return None

    conversion = Conversion.objects.filter(currency_from=currency_from, currency_to=currency_to).first()
    if conversion:
        return conversion.price_per


def convert_price(current_price: float | Decimal | int, price_per: Decimal, divide: bool = False):
    if not isinstance(current_price, Decimal):
        current_price = Decimal(current_price)

    if divide:
        return Decimal(current_price) / Decimal(price_per)
    return Decimal(current_price) * Decimal(price_per)


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


def get_translated_text(select_lang, target_lang, text: str):
    url = 'https://translate.googleapis.com/translate_a/single?client=gtx&dt=t&sl=%s&tl=%s&q=%s'
    response = requests.get(url % (select_lang, target_lang, text))
    return response.json()[0][0][0]


def is_japanese_char(char):
    # Normalize the character to NFKC form to handle different representations
    normalized_char = unicodedata.normalize('NFKC', char)

    # Check if the normalized character is a Japanese character
    # Hiragana: U+3040 to U+309F
    # Katakana: U+30A0 to U+30FF
    # Kanji: U+4E00 to U+9FFF
    japanese_ranges = [
        (0x3040, 0x309F),
        (0x30A0, 0x30FF),
        (0x4E00, 0x9FFF)
    ]

    for start, end in japanese_ranges:
        for code_point in range(start, end + 1):
            if normalized_char == chr(code_point):
                return True

    return False


def get_tuple_from_query_param(param_value: str) -> tuple[str]:
    return tuple(value for value in param_value.replace(' ', '').split(',') if value.strip())
