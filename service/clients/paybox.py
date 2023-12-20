import hashlib
from typing import Literal, Any

import xmltodict
from requests import Response

from service.clients.base import BaseAPIClient


class PayboxAPI(BaseAPIClient):
    BASE_URL = "https://api.paybox.money"

    def __init__(self, merchant_id, secret_key):
        self._merchant_id = merchant_id
        self._secret = secret_key
        super().__init__()

    def _make_signature(self, path_name: str, payload: dict[str, Any]):
        values = [path_name]
        values += [payload[key] for key in sorted(payload)]
        values.append(self._secret)
        print(values)
        return hashlib.md5(";".join(values).encode()).hexdigest()

    def process_response(self, response: Response) -> Any:
        return xmltodict.parse(response.content)

    def init_transaction(
        self,
        order_id: str | int,
        amount: str | float | int,
        description: str,
        salt: str,
        currency: Literal["KGS", "USD", "JYE"],
        result_url: str = None,
        success_url: str = None,
        failure_url: str = None,
        **custom_params
    ):
        assert all(isinstance(v, str) for v in custom_params.values())

        payload = {
            "pg_merchant_id": self._merchant_id,
            "pg_order_id": str(order_id),
            "pg_amount": str(amount),
            "pg_currency": currency,
            "pg_salt": salt,
            "pg_description": description,
            **custom_params
        }
        if result_url:
            payload["pg_result_url"] = result_url
            payload["pg_request_method"] = "POST"

        if success_url:
            payload["pg_success_url"] = success_url
            payload["pg_success_url_method"] = "GET"
        if failure_url:
            payload["pg_failure_url"] = failure_url
            payload["pg_failure_url_method"] = "GET"

        payload["pg_sig"] = self._make_signature("init_payment.php", payload)
        return self.post("/init_payment.php", json=payload)

    def get_transaction_status(self, payment_id, order_id, salt: str):
        payload = {
            "pg_merchant_id": self._merchant_id,
            "pg_payment_id": payment_id,
            "pg_order_id": order_id,
            "pg_salt": salt
        }
        payload["pg_sig"] = self._make_signature("get_status3.php", payload)
        return self.post("/get_status3.php", json=payload)
