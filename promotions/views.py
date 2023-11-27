from django.conf import settings
from drf_spectacular.utils import extend_schema, extend_schema_view
from rest_framework import generics, filters
from rest_framework.generics import get_object_or_404
from rest_framework.permissions import AllowAny

from products.models import Product
from products.serializers import ShortProductSerializer
from service.filters import SiteFilter
from service.mixins import CurrencyMixin
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
class PromotionProductListView(CurrencyMixin, generics.ListAPIView):
    permission_classes = (AllowAny,)
    promotion_queryset = Promotion.objects.active_promotions().filter(products__isnull=False)
    serializer_class = ShortProductSerializer
    pagination_class = PagePagination
    lookup_url_kwarg = 'promotion_id'
    lookup_field = 'id'
    filter_backends = (filters.OrderingFilter,)
    ordering_fields = ('created_at',)

    def get_promotion(self):
        filter_kwargs = {self.lookup_field: self.kwargs[self.lookup_url_kwarg]}
        promotion = get_object_or_404(self.promotion_queryset, **filter_kwargs)
        self.check_object_permissions(self.request, promotion)
        return promotion

    def get_queryset(self):
        return self.get_promotion().products.filter(is_active=True)


@extend_schema_view(get=extend_schema(parameters=[settings.CURRENCY_QUERY_SCHEMA_PARAM]))
class DiscountProductListView(CurrencyMixin, generics.ListAPIView):
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
