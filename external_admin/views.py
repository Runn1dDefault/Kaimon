from django.db import transaction
from django.utils.translation import gettext_lazy as _
from drf_spectacular.utils import extend_schema
from rest_framework import generics, mixins, viewsets, status, filters, parsers
from rest_framework.decorators import action
from rest_framework.filters import SearchFilter, OrderingFilter
from rest_framework.generics import get_object_or_404
from rest_framework.parsers import MultiPartParser, FormParser, JSONParser
from rest_framework.response import Response

from products.views import CategoryViewSet
from service.models import Conversion
from products.models import Product, ProductReview, Tag, Category
from promotions.models import Promotion
from users.models import User
from order.models import Order
from service.mixins import CachingMixin
from service.filters import FilterByFields, DateRangeFilter, ListFilter

from .mixins import DirectorViewMixin, StaffViewMixin
from .paginators import UserListPagination, AdminPagePagination
from .serializers import (
    ConversionAdminSerializer, PromotionAdminSerializer,
    ProductAdminSerializer, ProductDetailAdminSerializer,
    ProductImageAdminSerializer, UserAdminSerializer, TagAdminSerializer,
    ProductReviewAdminSerializer, OrderAnalyticsSerializer, UserAnalyticsSerializer, ReviewAnalyticsSerializer,
    OrderAdminSerializer, CategoryAdminSerializer
)


# ---------------------------------------------- Users -----------------------------------------------------------------
class UserAdminViewSet(DirectorViewMixin, viewsets.ModelViewSet):
    queryset = User.objects.filter(role=User.Role.CLIENT)
    pagination_class = UserListPagination
    serializer_class = UserAdminSerializer
    filter_backends = (SearchFilter, DateRangeFilter)
    search_fields = ('email', 'full_name', 'id')
    start_field = 'date_joined__date'
    start_param = 'start_date'
    end_field = 'date_joined__date'
    end_param = 'end_date'
    lookup_url_kwarg = 'user_id'
    lookup_field = 'id'


# ------------------------------------------------ Categories ----------------------------------------------------------
class CategoryListAdminView(StaffViewMixin, CategoryViewSet):
    queryset = Category.objects.all()
    serializer_class = CategoryAdminSerializer
    pagination_class = AdminPagePagination

    @extend_schema(responses={status.HTTP_204_NO_CONTENT: None})
    @action(methods=['GET'], detail=True, url_path='change-activity')
    def activate_or_deactivate_genre(self, request, **kwargs):
        genre = self.get_object()
        genre.deactivated = not genre.deactivated
        genre.products.update(is_active=not genre.deactivated)
        genre.save()
        return Response(status=status.HTTP_204_NO_CONTENT)


# -------------------------------------------------- Tag ---------------------------------------------------------------
class TagListAdminView(CachingMixin, StaffViewMixin, generics.ListAPIView):
    queryset = Tag.objects.filter(group__isnull=False)
    pagination_class = AdminPagePagination
    serializer_class = TagAdminSerializer
    filter_backends = (SearchFilter,)
    search_fields = ('id', 'name',)


# ----------------------------------------------- Product --------------------------------------------------------------
class ProductAdminViewSet(StaffViewMixin, viewsets.ModelViewSet):
    queryset = Product.objects.all()
    list_serializer_class = ProductAdminSerializer
    serializer_class = ProductDetailAdminSerializer
    pagination_class = AdminPagePagination
    parser_classes = (parsers.JSONParser,)
    lookup_url_kwarg = 'product_id'
    lookup_field = 'id'
    filter_backends = (filters.SearchFilter, ListFilter)
    search_fields = ('id', 'name', 'genres__name')

    def get_serializer_class(self):
        if self.request.method == 'GET' and self.detail is False:
            return self.list_serializer_class or self.serializer_class
        return self.serializer_class

    @extend_schema(responses={status.HTTP_204_NO_CONTENT: None})
    @action(
        methods=['POST'],
        detail=True,
        url_path='remove-image'
    )
    def remove_image(self, request, **kwargs):
        product = self.get_object()
        image_url = request.data.get('image')
        if not image_url:
            return Response({'image': [_('is required')]}, status=status.HTTP_400_BAD_REQUEST)

        image_fk = get_object_or_404(product.image_urls.all(), url=image_url)
        image_fk.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)

    @extend_schema(responses={status.HTTP_204_NO_CONTENT: None})
    @action(methods=['GET'], detail=True, url_path='change-activity')
    def activate_or_deactivate_product(self, request, **kwargs):
        genre = self.get_object()
        genre.is_active = not genre.is_active
        genre.save()
        return Response(status=status.HTTP_204_NO_CONTENT)

    @extend_schema(responses={status.HTTP_200_OK: None}, request=ProductImageAdminSerializer)
    @action(methods=['POST'], detail=False)
    def add_new_image(self, request, **kwargs):
        serializer = ProductImageAdminSerializer(
            data=request.data,
            many=False,
            context=self.get_serializer_context()
        )
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response(status=status.HTTP_200_OK)

    @extend_schema(responses={status.HTTP_204_NO_CONTENT: None})
    @action(
        methods=['DELETE'],
        detail=True,
        url_path=r'remove-tag/(?P<tag_id>.+)'
    )
    def remove_tag(self, request, **kwargs):
        tag_fk = get_object_or_404(
            self.get_object().tags.all(),
            tag_id=self.kwargs['tag_id']
        )
        tag_fk.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)

    @extend_schema(responses={status.HTTP_200_OK: None})
    @action(
        methods=['GET'],
        detail=True,
        url_path=r'add-tag/(?P<tag_id>.+)'
    )
    def add_tag(self, request, **kwargs):
        tag_id = self.kwargs['tag_id']
        if not Tag.objects.filter(id=tag_id).exists():
            return Response({'detail': _('Tag does with id %s not exist!') % tag_id})
        self.get_object().tags.add(tag_id)
        return Response(status=status.HTTP_200_OK)


# ---------------------------------------------- Reviews ---------------------------------------------------------------
class ProductReviewAdminViewSet(
    StaffViewMixin,
    mixins.RetrieveModelMixin,
    mixins.DestroyModelMixin,
    mixins.ListModelMixin,
    viewsets.GenericViewSet
):
    queryset = ProductReview.objects.all()
    serializer_class = ProductReviewAdminSerializer
    pagination_class = AdminPagePagination
    filter_backends = [FilterByFields, filters.SearchFilter, DateRangeFilter]
    filter_fields = {'is_read': {'db_field': 'is_read', 'type': 'boolean'},
                     'moderated': {'db_field': 'moderated', 'type': 'boolean'}}
    search_fields = ('user__email', 'product__id', 'comment')
    start_field = 'created_at__date'
    start_param = 'start_date'
    end_field = 'created_at__date'
    end_param = 'end_date'
    lookup_field = 'id'
    lookup_url_kwarg = 'review_id'

    @extend_schema(responses={status.HTTP_204_NO_CONTENT: None})
    @action(methods=['GET'], detail=True, url_path='change-activity')
    def activate_or_deactivate_review(self, request, **kwargs):
        review = self.get_object()
        review.moderated = not review.moderated
        review.save()
        return Response(status=status.HTTP_204_NO_CONTENT)

    @extend_schema(responses={status.HTTP_204_NO_CONTENT: None})
    @action(methods=['GET'], detail=True, url_path='mark-read')
    def set_read(self, request, **kwargs):
        review = self.get_object()
        review.is_read = True
        review.save()
        return Response(status=status.HTTP_204_NO_CONTENT)

    @action(methods=['GET'], detail=False, url_path='new-count')
    def new_count(self, request, **kwargs):
        return Response({'count': self.get_queryset().filter(is_read=False).count()})


# ---------------------------------------------- Order -----------------------------------------------------------------
class OrderAdminViewSet(StaffViewMixin, mixins.UpdateModelMixin, mixins.ListModelMixin, viewsets.GenericViewSet):
    queryset = Order.objects.all()
    serializer_class = OrderAdminSerializer
    pagination_class = AdminPagePagination
    lookup_field = 'id'
    lookup_url_kwarg = 'order_id'
    filter_backends = (SearchFilter, ListFilter, OrderingFilter, DateRangeFilter)
    search_fields = ('customer__email', 'customer__name', 'customer__phone')
    list_filter_fields = {'status': 'status'}
    ordering_fields = ('id', 'created_at')
    start_param, end_param = 'start_date', 'end_date'
    start_field, end_field = 'created_at__date', 'created_at__date'

    @action(methods=['GET'], detail=False, url_path='new-count')
    def new_count(self, request, **kwargs):
        queryset = self.get_queryset().filter(status=Order.Status.pending)
        return Response({'count': queryset.count()})

    # TODO: maybe we need add mark order success action


# ----------------------------------------------- Promotions -----------------------------------------------------------
class PromotionAdminViewSet(StaffViewMixin, viewsets.ModelViewSet):
    queryset = Promotion.objects.all()
    pagination_class = AdminPagePagination
    serializer_class = PromotionAdminSerializer
    parser_classes = (MultiPartParser, FormParser, JSONParser)
    lookup_field = 'id'
    lookup_url_kwarg = 'promotion_id'
    filter_backends = (SearchFilter, OrderingFilter)
    search_fields = ('banner__name',)
    ordering_fields = ('id', 'created_at',)

    def perform_create(self, serializer):
        with transaction.atomic():
            super().perform_create(serializer)

    @extend_schema(responses={status.HTTP_204_NO_CONTENT: None})
    @action(methods=['GET'], detail=True, url_path='change-activity')
    def deactivate_or_activate(self, request, **kwargs):
        promotion = self.get_object()
        promotion.deactivated = not promotion.deactivated
        promotion.save()
        return Response(status=status.HTTP_204_NO_CONTENT)


# ----------------------------------------- Currencies conversion ------------------------------------------------------
class ConversionAdminViewSet(
    DirectorViewMixin,
    mixins.ListModelMixin,
    mixins.UpdateModelMixin,
    viewsets.GenericViewSet
):
    queryset = Conversion.objects.all()
    serializer_class = ConversionAdminSerializer
    lookup_url_kwarg = 'conversion_id'
    lookup_field = 'id'


# ------------------------------------------------ Analytics -----------------------------------------------------------
class AnalyticsView(StaffViewMixin, generics.GenericAPIView):
    parser_classes = (parsers.FormParser, parsers.MultiPartParser, parsers.JSONParser)

    def get_analytics(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        return Response(serializer.data)

    def post(self, request, *args, **kwargs):
        return self.get_analytics(request, *args, **kwargs)


class OrderAnalyticsView(AnalyticsView):
    parser_classes = (parsers.JSONParser,)
    serializer_class = OrderAnalyticsSerializer


class UserAnalyticsView(AnalyticsView):
    serializer_class = UserAnalyticsSerializer


class ReviewAnalyticsView(AnalyticsView):
    serializer_class = ReviewAnalyticsSerializer
