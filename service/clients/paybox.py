import hashlib
from dataclasses import dataclass
from decimal import Decimal
from typing import Literal, Any

import xmltodict
from requests import Response

from service.clients.base import BaseAPIClient


@dataclass
class ReceiptPosition:
    # https://docs.paybox.money/?lang=ru#/payment-page/pay#content-%D0%BF%D0%BB%D0%B0%D1%82%D0%B5%D0%B6%D0%BD%D0%B0%D1%8F-%D1%81%D1%82%D1%80%D0%B0%D0%BD%D0%B8%D1%86%D0%B0
    name: str
    count: int
    price: float | Decimal
    tax_type: str = '0'

    def payload(self):
        return {
            "name": self.name,
            "count": str(self.count),
            "tax_type": self.tax_type,
            "price": str(self.price)
        }


class PayboxAPI(BaseAPIClient):
    BASE_URL = "https://api.freedompay.money"

    def __init__(self, merchant_id, secret_key):
        self._merchant_id = merchant_id
        self._secret = secret_key
        super().__init__()

    def _make_signature(self, payload: dict[str, Any]):
        values = ['init_payment.php']
        values += [v for k, v in sorted(payload.items())]
        values.append(self._secret)
        return hashlib.md5(';'.join(values).encode()).hexdigest()

    def process_response(self, response: Response) -> Any:
        return xmltodict.parse(response.content)

    def init_transaction(
        self,
        order_id: str,
        amount: str,
        description: str,
        salt: str,
        currency: Literal["KGS", "USD", "JYE"],
        result_url: str,
        success_url: str,
        failure_url: str,
        receipt_positions: list[ReceiptPosition] = None
    ):
        payload = {
            'pg_merchant_id': self._merchant_id,
            'pg_order_id': order_id,
            'pg_amount': amount,
            'pg_currency': currency,
            'pg_salt': salt,
            'pg_description': description,
            'pg_result_url': result_url,
            'pg_request_method': 'POST',
            'pg_success_url': success_url,
            'pg_failure_url': failure_url,
            'pg_success_url_method': 'GET',
            'pg_failure_url_method': 'GET',
        }
        if receipt_positions:
            payload['pg_receipt_positions'] = list(map(lambda x: x.payload(), receipt_positions))

        payload['pg_sig'] = self._make_signature(payload)
        return self.post('/init_payment.php', payload)
