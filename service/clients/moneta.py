import hashlib
import json
from functools import cached_property
from typing import Literal

from ecdsa import SigningKey, SECP256k1
from ecdsa.util import sigencode_der_canonize, sigdecode_der
from requests import Request

from service.clients.base import BaseAPIClient


class MonetaAPI(BaseAPIClient):
    ERROR_STATUSES = [400, 404, 500]

    def __init__(self, merchant_id: str, private_key: str):
        super().__init__(base_url="https://moneta.today/api/v1/")
        self.merchant_id = merchant_id
        self._private_key = private_key

    @cached_property
    def _key_pair(self) -> SigningKey:
        return SigningKey.from_string(bytes.fromhex(self._private_key), curve=SECP256k1)

    @property
    def _verifying_key(self):
        return self._key_pair.verifying_key

    def _make_signature(self, data: dict | list):
        signed_string = json.dumps(data, separators=(',', ':')).encode()
        signature = self._key_pair.sign_deterministic(
            signed_string,
            sigencode=sigencode_der_canonize,
            hashfunc=hashlib.sha256
        )
        # wrong verifying
        assert self._verifying_key.verify(
            signature,
            signed_string,
            sigdecode=sigdecode_der,
            hashfunc=hashlib.sha256
        ), "Wrong signature!"
        return signature.hex()

    def process_request(self, request: Request) -> None:
        request.headers["x-merchant-id"] = self.merchant_id

        if request.method == "POST":
            request.headers["x-public-key"] = self._verifying_key.to_string("compressed").hex()
            request.headers["x-request-sign"] = self._make_signature(request.json)

    def invoice(self, amount: float | int, meta: dict = None, coin: Literal["MONETA", "HEALTH"] = "HEALTH"):
        return self.post(
            "payment/invoice",
            json={
                "currency": coin,
                "amount": str(amount),
                "meta": meta or {}
            }
        )

    def status(self, invoice_id: str):
        return self.get("payment/status", params={"invoiceId": invoice_id})

    def health_usd_price_per(self):
        return self.get("coins/health/price")


if __name__ == "__main__":
    from pprint import pprint

    client = MonetaAPI(
        merchant_id="65df2795db23e06e6abb20f5",
        private_key="a396b54558e58a661668c65736c17a1d7a696ed9787e09cad8b1d96e8fc70b51"
    )

    data = client.invoice(1, meta={"title": "Test Invoice"})
    pprint(data)
