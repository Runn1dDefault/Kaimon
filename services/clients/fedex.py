import json
from dataclasses import dataclass, asdict
from datetime import timedelta, datetime
from enum import Enum
from typing import Literal, Iterable, Any
from urllib.parse import urljoin

from requests import Request

from services.clients.base import BaseAPIClient


@dataclass
class FedexAddress:
    # https://developer.fedex.com/api/en-kg/guides/api-reference.html#countrycodes
    country_code: str
    # https://developer.fedex.com/api/en-kg/catalog/rate/v1/docs.html#:~:text=here%20to%20see-,Postal,-aware%20countries
    postal_code: int | str = None
    city: str = None
    residential: bool = None
    # https://developer.fedex.com/api/en-kg/catalog/rate/v1/docs.html#:~:text=see%20State%20Or-,Province,-Code
    state_or_province_code: str = None

    def payload(self):
        payload = {
            "countryCode": self.country_code,
        }
        if self.postal_code:
            payload["postalCode"] = self.postal_code
        if self.city:
            payload['city'] = self.city
        if self.residential is not None:
            payload['residential'] = self.residential
        if self.state_or_province_code:
            payload['stateOrProvinceCode'] = self.state_or_province_code
        return payload


# https://developer.fedex.com/api/en-kg/catalog/rate/v1/docs.html#:~:text=here%20for%20more-,information,-on%20Pickup%20Types
class FedexPickupType(Enum):
    CONTACT_FEDEX_TO_SCHEDULE = 'CONTACT_FEDEX_TO_SCHEDULE'
    DROPOFF_AT_FEDEX_LOCATION = 'DROPOFF_AT_FEDEX_LOCATION'
    USE_SCHEDULED_PICKUP = 'USE_SCHEDULED_PICKUP'


# https://developer.fedex.com/api/en-us/guides/api-reference.html#packagetypes
class FedexPackagingType(Enum):
    YOUR_PACKAGING = 'YOUR_PACKAGING'
    FEDEX_ENVELOPE = 'FEDEX_ENVELOPE'
    FEDEX_BOX = 'FEDEX_BOX'
    FEDEX_SMALL_BOX = 'FEDEX_SMALL_BOX'
    FEDEX_MEDIUM_BOX = 'FEDEX_MEDIUM_BOX'
    FEDEX_LARGE_BOX = 'FEDEX_LARGE_BOX'
    FEDEX_EXTRA_LARGE_BOX = 'FEDEX_EXTRA_LARGE_BOX'
    FEDEX_10KG_BOX = 'FEDEX_10KG_BOX'
    FEDEX_25KG_BOX = 'FEDEX_25KG_BOX'
    FEDEX_PAK = 'FEDEX_PAK'
    FEDEX_TUBE = 'FEDEX_TUBE'


@dataclass
class FedexWeight:
    units: Literal['KG', 'LB']
    value: float | int

    def payload(self):
        return asdict(self)


@dataclass
class FedexCurrencyAmount:
    # https://developer.fedex.com/api/en-us/guides/api-reference.html#currencycodes
    currency: Literal['USD', 'JYE']
    amount: float | int = None

    def payload(self):
        return asdict(self)


@dataclass
class FedexCommodity:
    weight: FedexWeight
    currency_amount: FedexCurrencyAmount
    quantity: int = 1
    # https://developer.fedex.com/api/en-kg/guides/api-reference.html#harmonizedsystemcodeunitofmeasure-table1
    quantity_units: str = None
    # https://developer.fedex.com/api/en-kg/guides/api-reference.html#vaguecommoditydescriptions
    desciption: str = None
    
    def payload(self):
        payload = {
            "quantity": self.quantity,
            "weight": self.weight.payload(),
            "customsValue": self.currency_amount.payload()
        }
        if self.quantity_units:
            payload['quantityUnits'] = self.quantity_units
        if self.desciption:
            payload['description'] = self.desciption
        return payload


class FedexAPIClient(BaseAPIClient):
    BASE_URL = ''
    TEST_URL = 'https://apis-sandbox.fedex.com'
    ERROR_STATUSES = [400, 401, 500, 503]
    SECONDS_TO_SUBSTRACT = 5

    def __init__(self, client_id: str, client_secret: str, account_number: str = None, use_test: bool = False):
        super().__init__(self.BASE_URL if use_test is False else self.TEST_URL)
        self.account_number = account_number
        self._client_id = client_id
        self._client_secret = client_secret
        self._token = None
        self._token_exp = None

    def token_expired(self) -> bool:
        return not self._token_exp or datetime.utcnow() < self._token_exp

    def process_request(self, request) -> None:
        if not self._token or self.token_expired():
            self.auth()

        request.headers['Authorization'] = self._token
        request.headers['x-locale'] = 'en_US'
        request.headers['Content-Type'] = 'application/json'

    def auth(self) -> None:
        request = Request(
            method="POST",
            url=urljoin(self.base_url, '/oauth/token'),
            data={
                "grant_type": "client_credentials",
                "client_id": self._client_id,
                "client_secret": self._client_secret
            },
            headers={"Content-Type": "application/x-www-form-urlencoded"}
        )
        response = self.session.send(request.prepare())
        response_data = self.process_response(response)
        self._token = "%s %s" % (response_data['token_type'].title(), response_data['access_token'])
        self._token_exp = datetime.utcnow() + timedelta(seconds=response_data['expires_in'] - self.SECONDS_TO_SUBSTRACT)

    def international_rate_quotes(
        self,
        shipper: FedexAddress,
        recipient: FedexAddress,
        pickup_type: FedexPickupType,
        commodities: Iterable[FedexCommodity],
        ship_date: datetime.date
    ) -> dict[str, Any]:
        """
        docs: https://developer.fedex.com/api/en-us/catalog/rate/v1/docs.html#operation/Rate%20and%20Transit%20times
        """
        assert self.account_number, 'account_number is required for this action'
        payload = {
            "accountNumber": {
                "value": self.account_number
            },
            "requestedShipment": {
                "shipper": {"address": shipper.payload()},
                "recipient": {"address": recipient.payload()},
                "shipDateStamp": str(ship_date),
                "pickupType": pickup_type.value,
                # "preferredCurrency": "JYE",
                "serviceType": "INTERNATIONAL_PRIORITY",
                "rateRequestType": ["LIST", "ACCOUNT"],
                "customsClearanceDetail": {
                    "dutiesPayment": {
                        "paymentType": "SENDER",
                        "payor": {"responsibleParty": None}
                    },
                    "commodities": [c.payload() for c in commodities]
                },
                "requestedPackageLineItems": [{"weight": c.weight.payload()} for c in commodities]
            }
        }
        return self.post('/rate/v1/rates/quotes', json=payload)


if __name__ == '__main__':
    client = FedexAPIClient(
        client_id='l74d183751b6f54e14808394421c87c8d0',
        client_secret='442ffdc44b954f0393d6a57f3280b384',
        account_number='740561073',
        use_test=True
    )

    resp_data = client.international_rate_quotes(
        shipper=FedexAddress(postal_code="658-0032", country_code="JP"),
        recipient=FedexAddress(postal_code=720000, country_code="KG"),
        pickup_type=FedexPickupType.CONTACT_FEDEX_TO_SCHEDULE,
        commodities=(
            FedexCommodity(
                weight=FedexWeight(units="KG", value=10.0),
                currency_amount=FedexCurrencyAmount(currency='JYE', amount=100),
                desciption="Camera",
                quantity=1,
                quantity_units="PCS"
            ),
        ),
        ship_date=datetime(year=2023, month=11, day=15).date()
    )

    # with open('response.json', 'w') as json_file:
    #     json.dump(resp_data, json_file)

    ouput = resp_data['output']
    data = ouput['rateReplyDetails'][0]['ratedShipmentDetails'][0]
    
    print('quoteDate: ', ouput['quoteDate'])
    print('Base Rate: ', data['totalBaseCharge'])

    for i in data['shipmentRateDetail']['surCharges']:
        print(i['description'], ': ', i['amount'])

    for i in data['ancillaryFeesAndTaxes']:
        print(i['description'], ': ', i['amount'])

    print('Total Ancillary Fees And Taxes: ', data['totalAncillaryFeesAndTaxes'])
    print('Estimated Total: ', data['totalNetChargeWithDutiesAndTaxes'])
