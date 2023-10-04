from datetime import datetime, timedelta
from typing import Any
from urllib.parse import urljoin

from requests import Request
from services.clients.base import BaseClient


class CDEKClient(BaseClient):
    BASE_URL = 'https://api.cdek.ru'
    TEST_URL = 'https://api.edu.cdek.ru'
    ERROR_STATUSES = [400, 404, 429, 500, 503]

    def __init__(self, client_id: str, client_secret: str, use_test: bool = False):
        super().__init__(base_url=self.BASE_URL if use_test is False else self.TEST_URL)
        self.token = None
        self._expires_delta: datetime = datetime.utcnow()
        self.__client_id = client_id
        self.__client_secret = client_secret

    def process_request(self, request: Request) -> None:
        if not self.token or datetime.utcnow() >= self._expires_delta:
            self.auth()
        request.headers['Authorization'] = self.token
        request.headers['Content-Type'] = 'application/json'

    def auth(self) -> None:
        request = Request(
            'POST',
            url=urljoin(self.base_url, '/v2/oauth/token?parameters'),
            json={
                'grant_type': 'client_credentials',
                'client_id': self.__client_id,
                'client_secret': self.__client_secret
            }
        )
        response = self.process_response(self.session.send(request.prepare()))
        self.token = f'{response["token_type"].titile()} {response["access_token"]}'
        self._expires_delta = datetime.utcnow() + timedelta(seconds=response['expires_in'])

    def order_info(self, uuid: str, params: dict[str, Any]):
        return self.get(f'/v2/orders/{uuid}', params=params)

    def create_order(self, **body):
        return self.post('/v2/orders', json=body)

    def change_order(self, uuid: str, **body):
        body['uuid'] = uuid
        return self.patch('/v2/orders', json=body)

    def order_remove(self, uuid: str):
        return self.delete(f'/v2/orders/{uuid}')

    def order_refusal(self, uuid: str):
        return self.post(f'/v2/orders/{uuid}/refusal')
