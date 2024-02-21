import hashlib
import json
from functools import cached_property

from ecdsa import SigningKey, SECP256k1
from ecdsa.util import sigencode_der_canonize, sigdecode_der
from requests import Request

from service.clients.base import BaseAPIClient


class MonetaAPI(BaseAPIClient):
    def __init__(self, merchant_id: str, private_key: str):
        super().__init__(base_url="https://moneta.today/api/v1/payment/")
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

    def invoice(self, amount: float | int, meta: dict = None):
        return self.post(
            "invoice",
            json={
                "currency": "MONETA",
                "amount": str(amount),
                "meta": meta or {}
            }
        )

    def status(self, invoice_id: str):
        return self.get("status", params={"invoiceId": invoice_id})


if __name__ == "__main__":
    from pprint import pprint
    c = MonetaAPI(
        merchant_id="65aa57d8dfaa362db54f1de5",
        private_key="6c3d868cdb6792b4b6812f0857fdb26f7885afd47efcd56f4e8a9527777a179d"
    )
    data = c.invoice(
        amount=10,
        meta={"title": "Test Payment"}
    )
    pprint(data)

