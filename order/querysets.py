from django.contrib.postgres.aggregates import ArrayAgg
from django.db.models import F, Case, When, Value, Q, Sum
from django.db.models.functions import JSONObject, Round

from utils.querysets import AnalyticsQuerySet
from utils.types import AnalyticsFilter


def sale_price_calc_case(currency_field: str = None, from_receipt_obj: bool = True):
    if from_receipt_obj is False:
        discount_field = 'receipts__discount'
        quantity_field = 'receipts__quantity'
        unit_price_field = 'receipts__unit_price'
    else:
        discount_field = 'discount'
        quantity_field = 'quantity'
        unit_price_field = 'unit_price'

    discount_formula = ((F(discount_field) / F(unit_price_field)) * Value(100.0)) * F(quantity_field)
    simple_formula = F(unit_price_field) * F(quantity_field)

    if currency_field is not None:
        discount_formula *= F(currency_field)
        simple_formula *= F(currency_field)

    return Case(When(**{discount_field: 0}, then=Round(simple_formula, precision=2)),
                When(**{discount_field + '__gt': 0}, then=Round(discount_formula, precision=2)))


class OrderAnalyticsQuerySet(AnalyticsQuerySet):
    def total_prices(self):
        return self.annotate(
            yen=Sum(sale_price_calc_case(from_receipt_obj=False)),
            som=Sum(sale_price_calc_case('yen_to_som', from_receipt_obj=False)),
            dollar=Sum(sale_price_calc_case('yen_to_usd', from_receipt_obj=False))
        )

    def by_dates(self, by: AnalyticsFilter):
        return self.values(date=by.value('created_at')).annotate(
            receipts_info=ArrayAgg(
                JSONObject(
                    order_id=F('id'),
                    product_id=F('receipts__product_id'),
                    unit_price=F("receipts__unit_price"),
                    discount=F("receipts__discount"),
                    quantity=F('receipts__quantity'),
                    yen_to_som=F('yen_to_som'),
                    yen_to_dollar=F('yen_to_usd'),
                    status=F('status')
                )
            ),
            yen=Sum(sale_price_calc_case(from_receipt_obj=False)),
            som=Sum(sale_price_calc_case('yen_to_som', from_receipt_obj=False)),
            dollar=Sum(sale_price_calc_case('yen_to_usd', from_receipt_obj=False))
        )
