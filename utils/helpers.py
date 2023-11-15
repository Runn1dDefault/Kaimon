import uuid
from datetime import datetime
from decimal import Decimal


def import_model(model_import_path: str):
    assert '.' in model_import_path

    package = model_import_path.split('.')
    model_name = package[-1]
    mod = __import__('.'.join(package[:-1]), fromlist=[model_name])
    return getattr(mod, model_name)


def increase_price(price, percentage):
    if percentage > 0:
        return price + (Decimal(percentage) * Decimal(price) / 100)
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


def internal_uid_generation():
    """
    a function that returns a new uuid4 with the prefix internal: at the beginning.
    The prefix can be useful for separating manually created products from other ones
    """
    return 'internal:' + str(uuid.uuid4())


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
