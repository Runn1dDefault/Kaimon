import re
from enum import Enum


class CountryPostalCodePattern(Enum):
    KG = r'^\d{6}$'

    @classmethod
    def validate(cls, county_code: str, postal_code: str) -> bool:
        pattern = getattr(cls, county_code)
        if pattern:
            # Check if the postal code matches the pattern
            return re.match(pattern.value, postal_code) is not None
        return False


class Site(Enum):
    rakuten = 'rakuten'
    uniqlo = 'uniqlo'

    @classmethod
    def from_string(cls, site: str):
        by_value = {item.value: item for item in Site}
        return by_value[site]

    @classmethod
    def from_instance_id(cls, obj_id: str):
        return cls.from_string(obj_id.split('_')[0])


class SiteCurrency(Enum):
    rakuten = "yen"
    uniqlo = "usd"

    @classmethod
    def from_string(cls, site: str | Site):
        if isinstance(site, Site):
            site = site.value
        return getattr(cls, site)


class Spider(Enum):
    rakuten = Site.rakuten.value
    rakuten_category = 'rakuten_category'
    uniqlo = Site.uniqlo.value
    uniqlo_category = 'uniqlo_category'

