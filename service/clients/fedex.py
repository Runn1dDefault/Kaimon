from dataclasses import dataclass, asdict
from datetime import timedelta, datetime
from enum import Enum
from typing import Literal, Iterable, Any
from urllib.parse import urljoin

from requests import Request

from service.clients.base import BaseAPIClient


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
class FedexDimension:
    width: int
    length: int
    height: int
    units: Literal["CM", "IN"] = "CM"

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
class FedexRequestedPackageLineItem:
    weight: FedexWeight
    dimensions: FedexDimension
    group_package_count: int = 1
    physical_packaging: str = "YOUR_PACKAGING"

    def payload(self):
        return {
            "groupPackageCount": self.group_package_count,
            "physicalPackaging": self.physical_packaging,
            "insuredValue": {
                "currency": "JYE",
                "currencySymbol": None,
                "amount": 0
            },
            "weight": self.weight.payload(),
            "dimensions": self.dimensions.payload()
        }


@dataclass
class FedexCommodity:
    weight: FedexWeight
    currency_amount: FedexCurrencyAmount
    quantity: int = 1

    def payload(self):
        payload = {
            "name": "NON_DOCUMENTS",
            "numberOfPieces": 1,
            "description": "",
            "countryOfManufacture": "",
            "harmonizedCode": "",
            "harmonizedCodeDescription": "",
            "itemDescriptionForClearance": "",
            "weight": self.weight.payload(),
            "quantity": self.quantity,
            "quantityUnits": "",
            "unitPrice": self.currency_amount.payload(),
            "unitsOfMeasures": [
                {
                    "category": "",
                    "code": "",
                    "name": "",
                    "value": "",
                    "originalCode": ""
                }
            ],
            "excises": [{"values": [""], "code": ""}],
            "customsValue": {
                "currency": "JYE",
                "amount": 1,
                "currencySymbol": ""
            },
            "exportLicenseNumber": "",
            "partNumber": "",
            "exportLicenseExpirationDate": "",
            "getcIMarksAndNumbers": ""
        }
        return payload


class FedexAPIClient(BaseAPIClient):
    BASE_URL = 'https://apis.fedex.com'
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
        commodities: Iterable[FedexCommodity],
        ship_date: datetime.date,
        package_line_items: Iterable[FedexRequestedPackageLineItem]
    ) -> dict[str, Any]:
        """
        docs: https://developer.fedex.com/api/en-us/catalog/rate/v1/docs.html#operation/Rate%20and%20Transit%20times
        """
        assert self.account_number, 'account_number is required for this action'
        payload = {
            "accountNumber": {
                "value": self.account_number
            },
            "rateRequestControlParameters": {
                "rateSortOrder": "COMMITASCENDING",
                "returnTransitTimes": True,
                "variableOptions": None,
                "servicesNeededOnRateFailure": False
            },
            "requestedShipment": {
                "shipper": {"address": shipper.payload()},
                "recipient": {"address": recipient.payload()},
                "shipDateStamp": str(ship_date),
                "pickupType": "CONTACT_FEDEX_TO_SCHEDULE",
                "packagingType": "YOUR_PACKAGING",
                "serviceType": "FEDEX_INTERNATIONAL_PRIORITY",
                "rateRequestType": ["ACCOUNT"],
                "requestedPackageLineItems": [item.payload() for item in package_line_items],
                "preferredCurrency": "JYE",
                "customsClearanceDetail": {
                    "dutiesPayment": {"paymentType": "SENDER", "payor": {"responsibleParty": None}},
                    "commodities": [commodity.payload() for commodity in commodities]
                },
            },
            "carrierCodes": ["FDXG", "FDXE"]
        }
        return self.post('/rate/v1/rates/quotes', json=payload)


if __name__ == '__main__':
    import json

    client = FedexAPIClient(
        client_id='l7766482a2061f4738b06386df74defc41',
        client_secret='a6e57a4975074e5da35d01873355c3bc',
        account_number='515281100',
        use_test=False
    )

    resp_data = client.international_rate_quotes(
        shipper=FedexAddress(postal_code="658-0032", country_code="JP", residential=False),
        recipient=FedexAddress(postal_code="0000", country_code="KG", city="Bishkek", residential=False),
        commodities=(
            FedexCommodity(
                weight=FedexWeight(units="KG", value=0.300),
                currency_amount=FedexCurrencyAmount(currency='JYE', amount=5),
                quantity=1
            ),
        ),
        ship_date=datetime(year=2023, month=11, day=30).date(),
        package_line_items=(
            FedexRequestedPackageLineItem(
                weight=FedexWeight(units="KG", value=0.300),
                dimensions=FedexDimension(width=10, length=10, height=10)
            ),
        )
    )
    # with open('response.json', 'w') as json_file:
    #     json.dump(resp_data, json_file)

    data = resp_data['output']['rateReplyDetails'][0]
    commit = data['commit']
    print('Service Name: ', data['serviceName'])
    print('Date: ', commit['dateDetail']['dayFormat'])
    print('Shipment Details: ')
    for rate in data['ratedShipmentDetails']:
        print('-----------------------------------------------------')
        print('\tType: ', rate['rateType'])
        currency = rate['currency']
        print('\tBase rate: ', rate['totalBaseCharge'], ' ', currency)

        shipment_detail = rate['shipmentRateDetail']

        for surcharge in shipment_detail['surCharges']:
            print('\t', surcharge['description'], ': ', surcharge['amount'])

        for discount in shipment_detail['freightDiscount']:
            print('\t', discount['description'], ': -', discount['amount'])

        print('\tTotal Estimate: ', rate['totalNetCharge'])
        print('\n\n')
