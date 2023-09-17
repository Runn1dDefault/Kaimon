from enum import Enum


class ProductSort(Enum):
    standard = 'standard'
    release_date = 'releaseDate'
    seller = 'seller'
    satisfied = 'satisfied'


class ItemSort(Enum):
    standard = 'standard'
    affiliate_rate_asc = '-affiliateRate'
    affiliate_rate_desc = '+affiliateRate'
    review_count_asc = '-reviewCount'
    review_count_desc = '+reviewCount'
    review_avg_asc = '-reviewAverage'
    review_avg_desc = '+reviewAverage'
    item_price_asc = '-itemPrice'
    item_price_desc = '+itemPrice'
    update_ts_asc = '-updateTimestamp'
    update_ts_desc = '+updateTimestamp'
