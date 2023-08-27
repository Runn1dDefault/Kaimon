from drf_spectacular.utils import extend_schema_view, extend_schema
from rest_framework import generics, permissions, filters

from order.filters import FilterByFields
from order.models import Order
from product.paginators import PagePagination
from utils.mixins import LanguageMixin
from utils.schemas import LANGUAGE_QUERY_SCHEMA_PARAM

from .serializers import AdminOrderSerializer


class OrderMixin:
    queryset = Order.objects.all()
    serializer_class = AdminOrderSerializer
    permission_classes = (permissions.IsAuthenticated, permissions.IsAdminUser)


@extend_schema_view(get=extend_schema(parameters=[LANGUAGE_QUERY_SCHEMA_PARAM]))
class OrderListView(LanguageMixin, OrderMixin, generics.ListAPIView):
    pagination_class = PagePagination
    filter_backends = [FilterByFields, filters.OrderingFilter]
    filter_fields = {
        'status': {'db_field': 'status', 'type': 'enum', 'choices': Order.Status.choices},
        'payed': {'db_field': 'is_payed', 'type': 'boolean'},
        'deleted': {'db_field': 'is_deleted', 'type': 'boolean'},
    }
    ordering_fields = ['id', 'created_at']


@extend_schema_view(get=extend_schema(parameters=[LANGUAGE_QUERY_SCHEMA_PARAM]))
class OrderSearchView(LanguageMixin, OrderMixin, generics.ListAPIView):
    pagination_class = PagePagination
    filter_backends = [filters.SearchFilter]
    search_fields = [
        'delivery_address__user__email',
        'delivery_address__user__full_name',
        'delivery_address__country__name',
        'delivery_address__country__name_ru',
        'delivery_address__country__name_en',
        'delivery_address__country__name_tr',
        'delivery_address__country__name_ky',
        'delivery_address__country__name_kz',
        'delivery_address__city',
        'delivery_address__phone',
        'delivery_address__zip_code',
        'receipts__product_name',
        'receipts__p_id'
    ]
