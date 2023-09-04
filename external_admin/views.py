from drf_spectacular.utils import extend_schema_view, extend_schema
from rest_framework import generics, mixins, viewsets, permissions, status, filters, parsers
from rest_framework.decorators import api_view, permission_classes
from rest_framework.filters import SearchFilter
from rest_framework.generics import get_object_or_404
from rest_framework.response import Response

from currencies.mixins import CurrencyMixin
from currencies.models import Conversion
from product.models import Product, ProductReview
from product.serializers import ProductListSerializer, ProductReviewSerializer
from promotions.serializers import PromotionSerializer
from users.models import User
from users.permissions import IsDirectorPermission
from order.models import Order
from utils.filters import FilterByFields
from utils.mixins import LanguageMixin
from utils.paginators import PagePagination
from utils.schemas import LANGUAGE_QUERY_SCHEMA_PARAM, CURRENCY_QUERY_SCHEMA_PARAM
from utils.views import PostAPIView

from .mixins import UserAdminViewMixin, OrderAdminViewMixin, PromotionAdminViewMixin
from .serializers import AdminConversionSerializer, PromotionCreateSerializer, PromotionAdminSerializer


# ---------------------------------------------- USERS -----------------------------------------------------------------
class UserListAdminView(UserAdminViewMixin, generics.ListAPIView):
    pass


class UserSearchAdminView(UserAdminViewMixin, generics.ListAPIView):
    filter_backends = [SearchFilter]
    search_fields = ['email', 'full_name', 'id']


@api_view(['GET'])
@permission_classes([permissions.IsAuthenticated, permissions.IsAdminUser])
def block_or_unblock_user_admin_view(request, user_id):
    if request.user.role == User.Role.DIRECTOR:
        queryset = User.objects.exclude(role=User.Role.DEVELOPER)
    else:
        queryset = User.objects.filter(role=User.Role.CLIENT)
    user = get_object_or_404(queryset, id=user_id)
    user.is_active = not user.is_active
    user.save()
    return Response(status=status.HTTP_204_NO_CONTENT)


# --------------------------------------------- PRODUCT ----------------------------------------------------------------
@extend_schema_view(get=extend_schema(parameters=[LANGUAGE_QUERY_SCHEMA_PARAM]))
class ProductListAdminView(LanguageMixin, generics.ListAPIView):
    queryset = Product.objects.filter(is_active=True)
    permission_classes = [permissions.IsAuthenticated, permissions.IsAdminUser]
    serializer_class = ProductListSerializer
    pagination_class = PagePagination


class ProductReviewAdminView(mixins.DestroyModelMixin, mixins.ListModelMixin, viewsets.GenericViewSet):
    queryset = ProductReview.objects.filter(is_active=True)
    permission_classes = [permissions.IsAuthenticated, permissions.IsAdminUser]
    filter_backends = [FilterByFields]
    serializer_class = ProductReviewSerializer
    pagination_class = PagePagination
    lookup_field = 'id'
    filter_fields = {'is_read': {'db_field': 'is_read', 'type': 'boolean'}}

    def perform_destroy(self, instance):
        instance.is_active = False
        instance.save()


@api_view(['GET'])
@permission_classes([permissions.IsAuthenticated, permissions.IsAdminUser])
def get_new_reviews_count(request):
    return Response({'count': ProductReview.objects.filter(is_active=True, is_read=False).count()})


# ---------------------------------------------- ORDER -----------------------------------------------------------------
@extend_schema_view(get=extend_schema(parameters=[LANGUAGE_QUERY_SCHEMA_PARAM]))
class AdminOrderListView(LanguageMixin, OrderAdminViewMixin, generics.ListAPIView):
    pagination_class = PagePagination
    filter_backends = [FilterByFields, filters.OrderingFilter]
    filter_fields = {
        'status': {'db_field': 'status', 'type': 'enum', 'choices': Order.Status.choices},
        'payed': {'db_field': 'is_payed', 'type': 'boolean'},
        'deleted': {'db_field': 'is_deleted', 'type': 'boolean'},
    }
    ordering_fields = ['id', 'created_at']


@extend_schema_view(get=extend_schema(parameters=[LANGUAGE_QUERY_SCHEMA_PARAM]))
class AdminOrderSearchView(LanguageMixin, OrderAdminViewMixin, generics.ListAPIView):
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


@api_view(['GET'])
@permission_classes([permissions.IsAuthenticated, permissions.IsAdminUser])
def update_order_to_delivered(request, order_id):
    order = get_object_or_404(queryset=Order.objects.all(), id=order_id)
    order.status = Order.Status.delivered
    order.save()
    return Response(status=status.HTTP_204_NO_CONTENT)


@api_view(['GET'])
@permission_classes([permissions.IsAuthenticated, permissions.IsAdminUser])
def update_order_to_success(request, order_id):
    order = get_object_or_404(queryset=Order.objects.all(), id=order_id)
    order.status = Order.Status.success
    order.save()
    return Response(status=status.HTTP_204_NO_CONTENT)


# ----------------------------------------------- PROMOTIONS -----------------------------------------------------------
@extend_schema_view(get=extend_schema(parameters=[LANGUAGE_QUERY_SCHEMA_PARAM]))
class PromotionListAdminView(
    LanguageMixin,
    PromotionAdminViewMixin,
    generics.ListAPIView
):
    pagination_class = PagePagination
    serializer_class = PromotionSerializer


@extend_schema_view(get=extend_schema(parameters=[CURRENCY_QUERY_SCHEMA_PARAM, LANGUAGE_QUERY_SCHEMA_PARAM]))
class PromotionRetrieveAdminView(
    CurrencyMixin,
    LanguageMixin,
    PromotionAdminViewMixin,
    generics.RetrieveAPIView
):
    serializer_class = PromotionAdminSerializer


@extend_schema_view(post=extend_schema(responses=PromotionAdminSerializer(many=True)))
class PromotionCreateAdminView(PromotionAdminViewMixin, PostAPIView):
    serializer_class = PromotionCreateSerializer
    parser_classes = [parsers.MultiPartParser]


class PromotionDeleteAdminView(PromotionAdminViewMixin, generics.DestroyAPIView):
    lookup_field = 'id'


# ----------------------------------------- CURRENCIES CONVERSIONS -----------------------------------------------------
class ConversionListAdminView(generics.ListAPIView):
    queryset = Conversion.objects.all().order_by('-id')
    permission_classes = [permissions.IsAuthenticated, IsDirectorPermission]
    serializer_class = AdminConversionSerializer


class UpdateConversionAdminView(generics.UpdateAPIView):
    queryset = Conversion.objects.all()
    permission_classes = [permissions.IsAuthenticated, IsDirectorPermission]
    serializer_class = AdminConversionSerializer
