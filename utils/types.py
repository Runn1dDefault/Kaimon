from enum import Enum

from django.db.models.functions import TruncDate, TruncMonth, TruncYear, TruncDay


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
                return AnalyticsFilter.DATE
            case 'month':
                return AnalyticsFilter.MONTH
            case 'year':
                return AnalyticsFilter.YEAR
