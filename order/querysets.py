from enum import Enum

from django.contrib.postgres.aggregates import ArrayAgg
from django.db.models import QuerySet, F, Case, When, Value
from django.db.models.functions import TruncMonth, TruncDate, TruncDay, TruncYear, JSONObject, Round
from pandas import DataFrame


class AnalyticsFilter(Enum):
    DATE = TruncDate
    MONTH = TruncMonth
    YEAR = TruncYear
    DAY = TruncDay

    @classmethod
    def get_by_string(cls, by: str):
        check_field = by.lower()
        if check_field not in ('day', 'month', 'year'):
            raise ValueError('this filtering not supported %s' % by)

        match check_field:
            case 'day':
                return AnalyticsFilter.DAY
            case 'month':
                return AnalyticsFilter.MONTH
            case 'year':
                return AnalyticsFilter.YEAR


class OrderAnalyticsQuerySet(QuerySet):
    sale_formula = F('receipts__unit_price') - (F('receipts__discount') * F('receipts__unit_price') / Value(100.0))

    def total_prices_by_date(self, by: AnalyticsFilter):
        return self.values(date=by.value('created_at'), order_id=F('id')).annotate(
            receipts_info=ArrayAgg(
                JSONObject(
                    unit_price=F("receipts__unit_price"),
                    discount=F("receipts__discount"),
                    purchases_count=F('receipts__purchases_count')
                )
            ),
            sale_prices_yen=ArrayAgg(
              Case(
                  When(
                      receipts__discount=0,
                      then=Round(
                          F('receipts__unit_price') * F('receipts__purchases_count'),
                          precision=2
                      )
                  ),
                  When(
                      receipts__discount__gt=0,
                      then=Round(self.sale_formula * F('receipts__purchases_count'), precision=2)
                  )

              )
            ),
            sale_prices_som=ArrayAgg(
                Case(
                    When(
                        receipts__discount=0,
                        then=Round(
                            F('receipts__unit_price') * F('receipts__purchases_count') * F('yen_to_som'),
                            precision=2
                        )
                    ),
                    When(
                        receipts__discount__gt=0,
                        then=Round(self.sale_formula * F('receipts__purchases_count') * F('yen_to_som'), precision=2)
                    )

                )
            ),
            sale_prices_dollar=ArrayAgg(
                Case(
                    When(
                        receipts__discount=0,
                        then=Round(
                            F('receipts__unit_price') * F('receipts__purchases_count') * F('yen_to_usd'),
                            precision=2
                        )
                    ),
                    When(
                        receipts__discount__gt=0,
                        then=Round(self.sale_formula * F('receipts__purchases_count') * F('yen_to_usd'), precision=2)
                    )

                )
            )
        )

    def collected_total_prices(self, by: AnalyticsFilter):
        df = self.total_prices_by_date(by).to_df()
        df['total_price_yen'] = df['sale_prices_yen'].apply(lambda x: sum(x))
        df['total_price_som'] = df['sale_prices_som'].apply(lambda x: sum(x))
        df['total_price_dollar'] = df['sale_prices_dollar'].apply(lambda x: sum(x))
        df.set_index('date', inplace=True)
        df = df.stack().reset_index()
        # df.columns = ['order_id', 'receipts_info', 'total_price_yen', 'total_price_som', 'total_price_dollar']
        print(df)
        return df.to_dict()

    def to_df(self) -> DataFrame:
        return DataFrame(self)
