from django.utils.translation import gettext_lazy as _
from drf_spectacular.utils import extend_schema_view, extend_schema
from rest_framework import generics, mixins, viewsets, permissions, status, filters, parsers
from rest_framework.decorators import action
from rest_framework.filters import SearchFilter
from rest_framework.response import Response

from currencies.models import Conversion
from product.filters import SearchFilterByLang
from product.models import Product, ProductReview, Genre, Tag
from product.serializers import ProductReviewSerializer, GenreSerializer, TagSerializer
from promotions.models import Promotion
from users.models import User
from order.models import Order
from utils.filters import FilterByFields
from utils.mixins import LanguageMixin
from utils.paginators import PagePagination
from utils.schemas import LANGUAGE_QUERY_SCHEMA_PARAM
from .paginators import UserListPagination

from .serializers import ConversionAdminSerializer, PromotionAdminSerializer, \
    ProductAdminSerializer, ProductDetailAdminSerializer, OrderAdminSerializer, \
    ProductImageAdminSerializer, UserAdminSerializer


class AdminViewMixin:
    pass
    # permission_classes = (permissions.IsAuthenticated, permissions.IsAdminUser,)


# ---------------------------------------------- Users -----------------------------------------------------------------
class UserAdminView(AdminViewMixin, viewsets.ReadOnlyModelViewSet):
    queryset = User.objects.exclude(role=User.Role.DEVELOPER)
    pagination_class = UserListPagination
    serializer_class = UserAdminSerializer
    filter_backends = [SearchFilter]
    search_fields = ['email', 'full_name', 'id']

    @action(methods=['GET'], detail=True)
    def block_or_unblock_user(self):
        user = self.get_object()
        user.is_active = not user.is_active
        user.save()
        return Response(status=status.HTTP_202_ACCEPTED)


# --------------------------------------------- Product ----------------------------------------------------------------
@extend_schema_view(get=extend_schema(parameters=[LANGUAGE_QUERY_SCHEMA_PARAM]))
class ProductListAdminView(AdminViewMixin, LanguageMixin, generics.ListAPIView):
    queryset = Product.objects.all()
    serializer_class = ProductAdminSerializer
    pagination_class = PagePagination
    filter_backends = [SearchFilterByLang, filters.OrderingFilter]
    search_fields_ja = ['name', 'genres__name', 'tags__name']
    search_fields_ru = ['name_ru', 'genres__name_ru', 'tags__name_ru']
    search_fields_en = ['name_en', 'genres__name_en', 'tags__name_en']
    search_fields_tr = ['name_tr', 'genres__name_tr', 'tags__name_tr']
    search_fields_ky = ['name_ky', 'genres__name_ky', 'tags__name_ky']
    search_fields_kz = ['name_kz', 'genres__name_kz', 'tags__name_kz']
    ordering_fields = ['created_at', 'price', 'name', 'id', 'is_active']


@extend_schema_view(get=extend_schema(parameters=[LANGUAGE_QUERY_SCHEMA_PARAM]))
class ProductAdminViewSet(AdminViewMixin, mixins.RetrieveModelMixin, mixins.CreateModelMixin, mixins.UpdateModelMixin,
                          mixins.DestroyModelMixin, LanguageMixin, viewsets.GenericViewSet):
    lookup_url_kwarg = 'product_id'
    lookup_field = 'id'
    queryset = Product.objects.all()
    serializer_class = ProductDetailAdminSerializer
    pagination_class = PagePagination

    def destroy(self, request, *args, **kwargs):
        product = self.get_object()
        if product.receipts.exists():
            return Response(
                {'detail': _('This product has receipts or participates in orders, it cannot be deleted. '
                             'But you can deactivate it and users on the site won\'t '
                             'see it and won\'t be able to interact with it.')},
                status=status.HTTP_304_NOT_MODIFIED
            )
        self.perform_destroy(product)
        return Response(status=status.HTTP_204_NO_CONTENT)

    @extend_schema(responses={status.HTTP_204_NO_CONTENT: None})
    @action(
        methods=['DELETE'],
        detail=True,
        url_path=r'^remove-image/(?P<image_id>.+)'
    )
    def remove_image(self, request, **kwargs):
        product = self.get_object()
        image_id = self.kwargs.get('image_id')
        if not image_id:
            return Response({'detail': [_('image_id is required')]}, status=status.HTTP_400_BAD_REQUEST)
        image_query = product.image_urls.filter(id=image_id)
        if not image_query.exists():
            return Response({'detail': [_('image not found!')]}, status=status.HTTP_400_BAD_REQUEST)
        image_query.first().delete()
        return Response(status=status.HTTP_204_NO_CONTENT)

    @extend_schema(responses={status.HTTP_202_ACCEPTED: None}, request=ProductImageAdminSerializer)
    @action(methods=['POST'], detail=False)
    def add_new_image(self, request, **kwargs):
        serializer = ProductImageAdminSerializer(
            data=request.data,
            many=False,
            context=self.get_serializer_context()
        )
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response(status=status.HTTP_202_ACCEPTED)

    @extend_schema(responses={status.HTTP_204_NO_CONTENT: None})
    @action(
        methods=['DELETE'],
        detail=True,
        url_path=r'^remove-tag/(?P<tag_id>.+)'
    )
    def remove_tag(self, request, **kwargs):
        self.get_object().tags.remove(self.kwargs['tag_id'])
        return Response(status=status.HTTP_204_NO_CONTENT)

    @extend_schema(responses={status.HTTP_204_NO_CONTENT: None})
    @action(
        methods=['GET'],
        detail=True,
        url_path=r'^add-tag/(?P<tag_id>.+)'
    )
    def add_tag(self, request, **kwargs):
        tag_id = self.kwargs['tag_id']
        if not Tag.objects.filter(id=tag_id).exists():
            return Response({'detail': _('Tag does with id %s not exist!') % tag_id})
        product = self.get_object()
        product.tags.add(int(tag_id))
        product.save()
        return Response(status=status.HTTP_202_ACCEPTED)


# ------------------------------------------------ Genre ---------------------------------------------------------------
@extend_schema_view(get=extend_schema(parameters=[LANGUAGE_QUERY_SCHEMA_PARAM]))
class GenreSearchAdminView(AdminViewMixin, LanguageMixin, generics.ListAPIView):
    queryset = Genre.objects.all()
    serializer_class = GenreSerializer
    pagination_class = PagePagination
    filter_backends = [filters.SearchFilter]
    search_fields = ['name', 'name_tr', 'name_ru', 'name_en', 'name_ky', 'name_kz']


# -------------------------------------------------- Tag ---------------------------------------------------------------
@extend_schema_view(get=extend_schema(parameters=[LANGUAGE_QUERY_SCHEMA_PARAM]))
class TagSearchAdminView(AdminViewMixin, LanguageMixin, generics.ListAPIView):
    queryset = Tag.objects.all()
    pagination_class = PagePagination
    serializer_class = TagSerializer
    filter_backends = [filters.SearchFilter]
    search_fields = ['name', 'name_tr', 'name_ru', 'name_en', 'name_ky', 'name_kz']


# ---------------------------------------------- Reviews ---------------------------------------------------------------
class ProductReviewAdminView(AdminViewMixin, mixins.RetrieveModelMixin, mixins.DestroyModelMixin, mixins.ListModelMixin,
                             viewsets.GenericViewSet):
    queryset = ProductReview.objects.all()
    serializer_class = ProductReviewSerializer
    pagination_class = PagePagination
    lookup_field = 'id'
    lookup_url_kwarg = 'review_id'
    filter_backends = [FilterByFields, filters.SearchFilter]
    filter_fields = {
        'is_read': {'db_field': 'is_read', 'type': 'boolean'},
        'is_active': {'db_field': 'is_active', 'type': 'boolean'},
    }
    search_fields = ('user__email', 'product__id', 'comment')

    @action(methods=['PATCH'], detail=True)
    def activate_or_deactivate_review(self, request, **kwargs):
        review = self.get_object()
        review.is_active = not review.is_active
        review.save()
        return Response(status=status.HTTP_202_ACCEPTED)

    @action(methods=['PATCH'], detail=True, url_path='set-read')
    def set_read(self, request, **kwargs):
        review = self.get_object()
        review.is_read = True
        review.save()
        return Response(status=status.HTTP_202_ACCEPTED)

    @action(methods=['GET'], detail=False, url_path='new-reviews-count')
    def new_reviews_count(self, request, **kwargs):
        return Response({'count': self.get_queryset().filter(is_active=True, is_read=False).count()})


# ---------------------------------------------- Order -----------------------------------------------------------------
@extend_schema_view(get=extend_schema(parameters=[LANGUAGE_QUERY_SCHEMA_PARAM]))
class OrderAdminViewSet(AdminViewMixin, LanguageMixin, viewsets.ReadOnlyModelViewSet):
    queryset = Order.objects.all()
    serializer_class = OrderAdminSerializer
    pagination_class = PagePagination
    filter_backends = [filters.SearchFilter, FilterByFields, filters.OrderingFilter]
    filter_fields = {
        'status': {'db_field': 'status', 'type': 'enum', 'choices': Order.Status.choices},
        'payed': {'db_field': 'is_payed', 'type': 'boolean'},
        'deleted': {'db_field': 'is_deleted', 'type': 'boolean'},
    }
    ordering_fields = ['id', 'created_at']
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

    @action(methods=['PATCH'], detail=True)
    def update_status(self, request, **kwargs):
        order = self.get_object()
        order_status = request.query_params.get('status')
        if not order_status:
            return Response({'detail': [_('status is required')]}, status=status.HTTP_400_BAD_REQUEST)
        order.status = order_status
        order.save()
        return Response(status=status.HTTP_202_ACCEPTED)


# ----------------------------------------------- Promotions -----------------------------------------------------------
class PromotionAdminViewSet(AdminViewMixin, viewsets.ModelViewSet):
    queryset = Promotion.objects.filter(is_deleted=False)
    pagination_class = PagePagination
    serializer_class = PromotionAdminSerializer
    parser_classes = (parsers.FormParser, parsers.MultiPartParser, parsers.JSONParser)
    filter_backends = [filters.SearchFilter, FilterByFields, filters.OrderingFilter]
    search_fields = ['banner__name', 'banner__name_ru', 'banner__name_en', 'banner__name_tr', 'banner__name_ky',
                     'banner__name_kz']
    filter_fields = {'deactivated': {'db_field': 'deactivated', 'type': 'boolean'}}
    ordering_fields = ['id', 'created_at', 'start_date', 'end_date']

    def perform_destroy(self, instance):
        instance.is_deleted = True
        instance.deactivated = True
        instance.save()


# ----------------------------------------- Currencies conversion ------------------------------------------------------
class ConversionListAdminView(AdminViewMixin, generics.ListAPIView):
    queryset = Conversion.objects.all().order_by('-id')
    serializer_class = ConversionAdminSerializer


class UpdateConversionAdminView(AdminViewMixin, generics.UpdateAPIView):
    queryset = Conversion.objects.all()
    serializer_class = ConversionAdminSerializer
