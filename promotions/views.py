from django.conf import settings
from drf_spectacular.utils import extend_schema, extend_schema_view
from rest_framework import generics, filters
from rest_framework.generics import get_object_or_404
from rest_framework.permissions import AllowAny

from products.models import Product
from products.serializers import ShortProductSerializer
from service.filters import SiteFilter
from service.mixins import CurrencyMixin, CachingMixin
from service.paginations import PagePagination

from .models import Promotion
from .serializers import PromotionSerializer


class PromotionListView(generics.ListAPIView):
    permission_classes = (AllowAny,)
    queryset = Promotion.objects.active_promotions()
    serializer_class = PromotionSerializer
    filter_backends = (SiteFilter,)
    pagination_class = PagePagination


@extend_schema_view(get=extend_schema(parameters=[settings.CURRENCY_QUERY_SCHEMA_PARAM]))
class PromotionProductListView(CachingMixin, CurrencyMixin, generics.ListAPIView):
    permission_classes = (AllowAny,)
    promotion_queryset = Promotion.objects.active_promotions().filter(products__isnull=False).distinct()
    serializer_class = ShortProductSerializer
    pagination_class = PagePagination
    lookup_url_kwarg = 'promotion_id'
    lookup_field = 'id'
    filter_backends = (SiteFilter,)

    def get_promotion(self):
        promotions = self.filter_queryset(self.promotion_queryset)
        filter_kwargs = {self.lookup_field: self.kwargs[self.lookup_url_kwarg]}
        return get_object_or_404(promotions, **filter_kwargs)

    def get_queryset(self):
        return self.get_promotion().products.filter(is_active=True)

    @classmethod
    def get_cache_prefix(cls) -> str:
        return 'product'


@extend_schema_view(get=extend_schema(parameters=[settings.CURRENCY_QUERY_SCHEMA_PARAM]))
class DiscountProductListView(CachingMixin, CurrencyMixin, generics.ListAPIView):
    permission_classes = (AllowAny,)
    queryset = Product.objects.filter(
        is_active=True,
        promotion__isnull=False,
        promotion__deactivated=False,
        promotion__discount__isnull=False
    )
    serializer_class = ShortProductSerializer
    pagination_class = PagePagination
    filter_backends = (filters.OrderingFilter, SiteFilter)
    ordering_fields = ('created_at',)

    @classmethod
    def get_cache_prefix(cls) -> str:
        return 'product'
