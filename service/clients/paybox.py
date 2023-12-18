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
    tax_type: str = "0"

    def payload(self):
        return {
            "name": self.name,
            "count": str(self.count),
            "tax_type": self.tax_type,
            "price": str(self.price)
        }


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
        receipt_positions: list[ReceiptPosition] = None,
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
        if receipt_positions:
            payload["pg_receipt_positions"] = list(map(lambda x: x.payload(), receipt_positions))

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


if __name__ == "__main__":
    from pprint import pprint

    paybox = PayboxAPI(merchant_id="", secret_key="")
    # resp_data = paybox.init_transaction(
    #     order_id="2",
    #     amount="10",
    #     description="Оплата заказа №1",
    #     currency="USD",
    #     salt="kaimono.vip",
    #     transaction_uuid="999d7d41-c5ea-46a4-9c4a-e620410ff43b"
    # )
    # pprint(resp_data)

    # resp_data = paybox.get_transaction_status(
    #     payment_id="1066603760",
    #     order_id="24",
    #     salt="kaimono.vip"
    # )
    # pprint(resp_data)
