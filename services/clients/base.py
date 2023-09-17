import logging
from typing import Any
from urllib.parse import urljoin

from requests import Session, Request, Response
from requests.adapters import HTTPAdapter


class BaseClient:
    RETRIES: int = None
    LOG_FORMAT: str = "'%(asctime)s %(name)s %(levelname)s: %(message)s'"
    BASE_URL: str = None

    def __init__(self, base_url: str = None):
        if not base_url:
            assert self.BASE_URL
        self.base_url = base_url or self.BASE_URL
        self.session = Session()
        self.logger = logging.getLogger(self.__class__.__name__)
        self._setup_session()
        self._setup_logger()

    def _setup_logger(self):
        formatter = logging.Formatter(self.LOG_FORMAT)
        console_handler = logging.StreamHandler()
        console_handler.setFormatter(formatter)
        self.logger.addHandler(console_handler)

    def _setup_session(self):
        if isinstance(self.RETRIES, int) and self.RETRIES > 1:
            self.session.mount('http://', HTTPAdapter(max_retries=self.RETRIES))

    def _request(self, method: str, path: str, **kwargs):
        request = Request(method, urljoin(self.base_url, path), **kwargs)
        self.process_request(request)
        response = self.session.send(request.prepare())
        return self.process_response(response)

    def process_request(self, request: Request) -> None:
        pass

    def process_response(self, response: Response) -> Any:
        pass

    def get(self, path: str, params: dict[str, Any] = None) -> Any:
        return self._request('GET', path, params=params)

    def post(self, path: str, params: dict[str, Any] = None) -> Any:
        return self._request('POST', path, json=params)
