from typing import Iterable


def concat_to_upper_string(strings: Iterable[str], concat_value: str = ', '):
    return concat_value.join(map(lambda x: x.replace('_', ' ').upper(), strings))

