from django.contrib.postgres.aggregates import ArrayAgg
from django.db.models import F, Case, When, Value, ExpressionWrapper, Q
from django.db.models.functions import JSONObject, Round

from utils.querysets import AnalyticsQuerySet
from utils.types import AnalyticsFilter


class OrderAnalyticsQuerySet(AnalyticsQuerySet):
    sale_formula = F('receipts__unit_price') - (F('receipts__discount') * F('receipts__unit_price') / Value(100.0))
    receipts_sale_formula = F('unit_price') - (F('discount') * F('unit_price') / Value(100.0))

    def sale_price_case(self, currency_field: str = None, from_receipts: bool = False):
        if from_receipts:
            with_discount_formula = self.receipts_sale_formula * F('quantity')
            without_discount_formula = F('unit_price') * F('quantity')
            discount_zero_exp = Q(discount=0)
            discount_gt_zero_exp = Q(discount__gt=0)
        else:
            discount_zero_exp = Q(receipts__discount=0)
            discount_gt_zero_exp = Q(receipts__discount__gt=0)
            with_discount_formula = self.sale_formula * F('receipts__quantity')
            without_discount_formula = F('receipts__unit_price') * F('receipts__quantity')

        if currency_field is not None:
            with_discount_formula *= F(currency_field)
            without_discount_formula *= F(currency_field)

        return Case(When(discount_zero_exp, then=Round(without_discount_formula, precision=2)),
                    When(discount_gt_zero_exp, then=Round(with_discount_formula, precision=2)))

    def get_analytics(self, by: AnalyticsFilter):
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
            sale_prices_yen=ArrayAgg(self.sale_price_case(from_receipts=False)),
            sale_prices_som=ArrayAgg(self.sale_price_case('yen_to_som', from_receipts=False)),
            sale_prices_dollar=ArrayAgg(self.sale_price_case('yen_to_usd', from_receipts=False))
        )
