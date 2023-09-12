from django.contrib.postgres.aggregates import ArrayAgg
from django.db.models import F, Case, When, Value
from django.db.models.functions import JSONObject, Round

from utils.queryset import AnalyticsQuerySet
from utils.types import AnalyticsFilter


class OrderAnalyticsQuerySet(AnalyticsQuerySet):
    sale_formula = F('receipts__unit_price') - (F('receipts__discount') * F('receipts__unit_price') / Value(100.0))

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
            sale_prices_yen=ArrayAgg(
              Case(
                  When(
                      receipts__discount=0,
                      then=Round(
                          F('receipts__unit_price') * F('receipts__quantity'),
                          precision=2
                      )
                  ),
                  When(
                      receipts__discount__gt=0,
                      then=Round(self.sale_formula * F('receipts__quantity'), precision=2)
                  )

              )
            ),
            sale_prices_som=ArrayAgg(
                Case(
                    When(
                        receipts__discount=0,
                        then=Round(
                            F('receipts__unit_price') * F('receipts__quantity') * F('yen_to_som'),
                            precision=2
                        )
                    ),
                    When(
                        receipts__discount__gt=0,
                        then=Round(self.sale_formula * F('receipts__quantity') * F('yen_to_som'), precision=2)
                    )

                )
            ),
            sale_prices_dollar=ArrayAgg(
                Case(
                    When(
                        receipts__discount=0,
                        then=Round(
                            F('receipts__unit_price') * F('receipts__quantity') * F('yen_to_usd'),
                            precision=2
                        )
                    ),
                    When(
                        receipts__discount__gt=0,
                        then=Round(self.sale_formula * F('receipts__quantity') * F('yen_to_usd'), precision=2)
                    )

                )
            )
        )
