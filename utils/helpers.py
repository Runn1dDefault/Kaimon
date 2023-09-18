from datetime import datetime


def import_model(model_import_path: str):
    assert '.' in model_import_path

    package = model_import_path.split('.')
    model_name = package[-1]
    mod = __import__('.'.join(package[:-1]), fromlist=[model_name])
    return getattr(mod, model_name)


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
