from drf_spectacular.utils import extend_schema_view, extend_schema
from rest_framework import generics, parsers, permissions

from currency_conversion.mixins import CurrencyMixin
from promotions.models import Promotion
from promotions.serializers import PromotionSerializer
from users.permissions import IsDirectorPermission
from utils.mixins import LanguageMixin
from utils.paginators import PagePagination
from utils.schemas import LANGUAGE_QUERY_SCHEMA_PARAM, CURRENCY_QUERY_SCHEMA_PARAM
from utils.views import PostAPIView

from .serializers import PromotionCreateSerializer, PromotionAdminSerializer


class PromotionAdminMixin:
    queryset = Promotion.objects.all()
    include_all_products = True
    lookup_field = 'id'
    permission_classes = [permissions.IsAuthenticated, IsDirectorPermission]


@extend_schema_view(get=extend_schema(parameters=[LANGUAGE_QUERY_SCHEMA_PARAM]))
class PromotionAdminListView(
    LanguageMixin,
    PromotionAdminMixin,
    generics.ListAPIView
):
    pagination_class = PagePagination
    serializer_class = PromotionSerializer


@extend_schema_view(get=extend_schema(parameters=[CURRENCY_QUERY_SCHEMA_PARAM, LANGUAGE_QUERY_SCHEMA_PARAM]))
class PromotionAdminRetrieveView(
    CurrencyMixin,
    LanguageMixin,
    PromotionAdminMixin,
    generics.RetrieveAPIView
):
    serializer_class = PromotionAdminSerializer


@extend_schema_view(post=extend_schema(responses=PromotionAdminSerializer(many=True)))
class PromotionCreateAdminView(PromotionAdminMixin, PostAPIView):
    serializer_class = PromotionCreateSerializer
    parser_classes = [parsers.MultiPartParser]


class PromotionDeleteAdminView(PromotionAdminMixin, generics.DestroyAPIView):
    lookup_field = 'id'
