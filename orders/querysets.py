from django.contrib.postgres.aggregates import ArrayAgg
from django.db.models import F, Case, When, Value, DecimalField, Count
from django.db.models.functions import JSONObject, Round

from service.querysets import BaseAnalyticsQuerySet


def sale_price_calc_case():
    unit_field = F('receipts__unit_price')
    discount_field = F('receipts__discount')
    quantity_field = F('receipts__quantity')
    hundred = Value(100.0, output_field=DecimalField())
    # if you change some field types to FloatField, you will need to make changes
    discount_formula = (unit_field - (discount_field * unit_field) / hundred) * quantity_field
    return Case(
        When(receipts__discount=0, then=Round(unit_field * quantity_field, precision=2)),
        When(receipts__discount__gt=0, then=Round(discount_formula, precision=2))
    )


class OrderAnalyticsQuerySet(BaseAnalyticsQuerySet):
    def by_dates(self, by):

        return self.values(date=by.value('created_at')).annotate(
            receipts_info=ArrayAgg(
                JSONObject(
                    order_id=F('id'),
                    status=F('status'),
                    product_code=F('receipts__product_code'),
                    product_name=F('receipts__product_name'),
                    product_image=F('receipts__product_image'),
                    product_url=F('receipts__product_url'),
                    unit_price=F("receipts__unit_price"),
                    site_currency=F("receipts__site_currency"),
                    site_price=F("receipts__site_price"),
                    discount=F("receipts__discount"),
                    quantity=F('receipts__quantity'),
                    sale_price=sale_price_calc_case()
                )
            ),
            count=Count('id')
        )
