from drf_spectacular.utils import extend_schema, extend_schema_view
from rest_framework import generics

from currency_conversion.mixins import CurrencyMixin
from utils.mixins import LanguageMixin
from utils.paginators import PagePagination
from utils.schemas import LANGUAGE_QUERY_SCHEMA_PARAM, CURRENCY_QUERY_SCHEMA_PARAM
from .models import Promotion
from .serializers import PromotionSerializer, PromotionDetailSerializer


@extend_schema_view(get=extend_schema(parameters=[LANGUAGE_QUERY_SCHEMA_PARAM]))
class PromotionListView(LanguageMixin, generics.ListAPIView):
    queryset = Promotion.objects.active_promotions()
    serializer_class = PromotionSerializer
    pagination_class = PagePagination


@extend_schema_view(get=extend_schema(parameters=[LANGUAGE_QUERY_SCHEMA_PARAM, CURRENCY_QUERY_SCHEMA_PARAM]))
class PromotionRetrieveView(CurrencyMixin, LanguageMixin, generics.RetrieveAPIView):
    queryset = Promotion.objects.active_promotions()
    serializer_class = PromotionDetailSerializer
    lookup_field = 'id'
