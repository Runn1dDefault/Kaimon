from django.db import transaction
from django.utils.translation import gettext_lazy as _
from drf_spectacular.utils import extend_schema
from rest_framework import generics, mixins, viewsets, status, filters, parsers
from rest_framework.decorators import action
from rest_framework.filters import SearchFilter
from rest_framework.generics import get_object_or_404
from rest_framework.response import Response

from currencies.models import Conversion
from product.filters import PopularProductOrdering
from product.models import Product, ProductReview, Genre, Tag, ProductTag, TagGroup
from promotions.models import Promotion
from users.models import User
from order.models import Order
from utils.filters import FilterByFields, DateRangeFilter, ListFilterFields
from utils.views import CachingMixin

from .mixins import DirectorViewMixin, StaffViewMixin
from .paginators import UserListPagination, AdminPagePagination
from .serializers import (
    ConversionAdminSerializer, PromotionAdminSerializer,
    ProductAdminSerializer, ProductDetailAdminSerializer,
    ProductImageAdminSerializer, UserAdminSerializer, GenreAdminSerializer, TagAdminSerializer,
    ProductReviewAdminSerializer, OrderAnalyticsSerializer, UserAnalyticsSerializer, ReviewAnalyticsSerializer,
    OrderAdminSerializer, TagGroupAdminSerializer
)


# ---------------------------------------------- Users -----------------------------------------------------------------
class UserAdminViewSet(DirectorViewMixin, viewsets.ReadOnlyModelViewSet):
    queryset = User.objects.filter(role=User.Role.CLIENT)
    pagination_class = UserListPagination
    serializer_class = UserAdminSerializer
    filter_backends = [SearchFilter, DateRangeFilter]
    search_fields = ['email', 'full_name', 'id']
    start_field = 'date_joined__date'
    start_param = 'start_date'
    end_field = 'date_joined__date'
    end_param = 'end_date'
    lookup_url_kwarg = 'user_id'
    lookup_field = 'id'

    @extend_schema(responses={status.HTTP_202_ACCEPTED: None})
    @action(methods=['GET'], detail=True, url_path='change-activity')
    def block_or_unblock_user(self, request, **kwargs):
        user = self.get_object()
        user.is_active = not user.is_active
        user.save()
        return Response(status=status.HTTP_202_ACCEPTED)

    @extend_schema(responses={status.HTTP_202_ACCEPTED: None})
    @action(methods=['GET'], detail=True, url_path='mark-register-payed')
    def mark_payed(self, request):
        user = self.get_object()
        user.registration_payed = True
        user.save()
        return Response(status=status.HTTP_202_ACCEPTED)


# ------------------------------------------------ Genre ---------------------------------------------------------------
class GenreListAdminView(CachingMixin, StaffViewMixin, generics.ListAPIView):
    queryset = Genre.objects.all()
    serializer_class = GenreAdminSerializer
    pagination_class = AdminPagePagination
    filter_backends = [filters.SearchFilter]
    search_fields = ['name', 'name_tr', 'name_ru', 'name_en', 'name_ky', 'name_kz']

    @extend_schema(responses={status.HTTP_204_NO_CONTENT: None})
    @action(methods=['GET'], detail=True, url_path='change-activity')
    def activate_or_deactivate_genre(self, request, **kwargs):
        genre = self.get_object()
        genre.is_active = not genre.is_active
        genre.save()
        return Response(status=status.HTTP_202_ACCEPTED)


# -------------------------------------------------- Tag ---------------------------------------------------------------
class TagListAdminView(CachingMixin, StaffViewMixin, generics.ListAPIView):
    queryset = Tag.objects.all()
    pagination_class = AdminPagePagination
    serializer_class = TagAdminSerializer
    filter_backends = [SearchFilter]
    search_fields = ['name', 'name_tr', 'name_ru', 'name_en', 'name_ky', 'name_kz']


class TagGroupListAdminViewSet(CachingMixin, StaffViewMixin, mixins.ListModelMixin, viewsets.GenericViewSet):
    queryset = TagGroup.objects.all()
    pagination_class = AdminPagePagination
    serializer_class = TagGroupAdminSerializer
    lookup_field = 'id'
    lookup_url_kwarg = 'group_id'

    @extend_schema(responses={status.HTTP_200_OK: TagAdminSerializer(many=True)})
    @action(methods=['GET'], detail=True, url_path='tags')
    def group_tags(self, request, **kwargs):
        queryset = Tag.objects.filter(group_id=self.kwargs[self.lookup_url_kwarg or self.lookup_field])
        page = self.paginate_queryset(queryset)
        serializer = TagAdminSerializer(
            instance=page,
            many=True,
            context=self.get_serializer_context()
        )
        return self.get_paginated_response(serializer.data)


# ----------------------------------------------- Product --------------------------------------------------------------
class ProductAdminViewSet(StaffViewMixin, viewsets.ModelViewSet):
    queryset = Product.objects.all()
    list_serializer_class = ProductAdminSerializer
    serializer_class = ProductDetailAdminSerializer
    pagination_class = AdminPagePagination
    parser_classes = (parsers.JSONParser,)
    filter_backends = [filters.SearchFilter, PopularProductOrdering, filters.OrderingFilter]
    search_fields = [
        'name', 'genres__genre__name', 'tags__tag__name',
        'name_ru', 'genres__genre__name_ru', 'tags__tag__name_ru',
        'name_en', 'genres__genre__name_en', 'tags__tag__name_en',
        'name_tr', 'genres__genre__name_tr', 'tags__tag__name_tr',
        'name_ky', 'genres__genre__name_ky', 'tags__tag__name_ky',
        'name_kz', 'genres__genre__name_kz', 'tags__tag__name_kz'
    ]
    ordering_fields = ['created_at', 'price']
    lookup_url_kwarg = 'product_id'
    lookup_field = 'id'

    def get_serializer_class(self):
        if self.request.method == 'GET' and self.detail is False:
            return self.list_serializer_class or self.serializer_class
        return self.serializer_class

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
        url_path=r'remove-tag/(?P<tag_id>.+)'
    )
    def remove_tag(self, request, **kwargs):
        tag_fk = get_object_or_404(
            self.get_object().tags.all(),
            tag_id=self.kwargs['tag_id']
        )
        tag_fk.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)

    @extend_schema(responses={status.HTTP_202_ACCEPTED: None})
    @action(
        methods=['GET'],
        detail=True,
        url_path=r'add-tag/(?P<tag_id>.+)'
    )
    def add_tag(self, request, **kwargs):
        tag_id = self.kwargs['tag_id']
        if not Tag.objects.filter(id=tag_id).exists():
            return Response({'detail': _('Tag does with id %s not exist!') % tag_id})
        product = self.get_object()
        ProductTag.objects.create(product=product, tag_id=tag_id)
        return Response(status=status.HTTP_202_ACCEPTED)


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
                     'is_active': {'db_field': 'is_active', 'type': 'boolean'}}
    search_fields = ('user__email', 'product__id', 'comment')
    start_field = 'created_at__date'
    start_param = 'start_date'
    end_field = 'created_at__date'
    end_param = 'end_date'
    lookup_field = 'id'
    lookup_url_kwarg = 'review_id'

    @extend_schema(responses={status.HTTP_202_ACCEPTED: None})
    @action(methods=['GET'], detail=True, url_path='change-activity')
    def activate_or_deactivate_review(self, request, **kwargs):
        review = self.get_object()
        review.is_active = not review.is_active
        review.save()
        return Response(status=status.HTTP_202_ACCEPTED)

    @extend_schema(responses={status.HTTP_202_ACCEPTED: None})
    @action(methods=['GET'], detail=True, url_path='mark-read')
    def set_read(self, request, **kwargs):
        review = self.get_object()
        review.is_read = True
        review.save()
        return Response(status=status.HTTP_202_ACCEPTED)


# ---------------------------------------------- Order -----------------------------------------------------------------
class OrderAdminViewSet(StaffViewMixin, viewsets.ReadOnlyModelViewSet):
    queryset = Order.objects.all()
    serializer_class = OrderAdminSerializer
    pagination_class = AdminPagePagination
    filter_backends = [filters.SearchFilter, ListFilterFields, filters.OrderingFilter, DateRangeFilter]
    list_filter_fields = {'status': 'status'}
    start_param = 'start_date'
    end_param = 'end_date'
    start_field = 'created_at__date'
    end_field = 'created_at__date'
    ordering_fields = ['id', 'created_at']
    search_fields = ['customer__email', 'customer__name', 'customer__phone']
    lookup_field = 'id'
    lookup_url_kwarg = 'order_id'

    @extend_schema(responses={status.HTTP_202_ACCEPTED: None})
    @action(methods=['GET'], detail=True, url_path="mark-in-delivering")
    def mark_in_delivering_order(self, request, **kwargs):
        order = self.get_object()
        if order.status != Order.Status.in_process:
            return Response({'detail': _('To update you need to set the %s' % Order.Status.in_process.value)})
        order.status = Order.Status.in_delivering
        order.save()
        return Response(status=status.HTTP_202_ACCEPTED)

    @extend_schema(responses={status.HTTP_202_ACCEPTED: None})
    @action(methods=['GET'], detail=True, url_path="mark-in-process")
    def mark_in_process_order(self, request, **kwargs):
        order = self.get_object()
        if order.status != Order.Status.pending:
            return Response({'detail': _('To update you need to set the %s' % Order.Status.pending.value)})
        order.status = Order.Status.in_process
        order.save()
        return Response(status=status.HTTP_202_ACCEPTED)

    @extend_schema(responses={status.HTTP_202_ACCEPTED: None})
    @action(methods=['GET'], detail=True, url_path="mark-reject")
    def mark_reject_order(self, request, **kwargs):
        order = self.get_object()
        if order.status in (Order.Status.pending, Order.Status.in_process):
            return Response({'detail': _('Cannot update order status')})
        order.status = Order.Status.rejected
        order.save()
        return Response(status=status.HTTP_202_ACCEPTED)

    # TODO: maybe we need add mark order success action


# ----------------------------------------------- Promotions -----------------------------------------------------------
class PromotionAdminViewSet(StaffViewMixin, viewsets.ModelViewSet):
    queryset = Promotion.objects.filter(is_deleted=False)
    pagination_class = AdminPagePagination
    serializer_class = PromotionAdminSerializer
    parser_classes = (parsers.MultiPartParser, parsers.FormParser, parsers.JSONParser)
    filter_backends = [filters.SearchFilter, FilterByFields, filters.OrderingFilter]
    search_fields = ['banner__name', 'banner__name_ru', 'banner__name_en', 'banner__name_tr', 'banner__name_ky',
                     'banner__name_kz']
    filter_fields = {'deactivated': {'db_field': 'deactivated', 'type': 'boolean'}}
    ordering_fields = ['id', 'created_at', 'start_date', 'end_date']
    lookup_field = 'id'
    lookup_url_kwarg = 'promotion_id'

    def perform_create(self, serializer):
        with transaction.atomic():
            super().perform_create(serializer)

    def perform_destroy(self, instance):
        instance.is_deleted = True
        instance.deactivated = True
        instance.save()


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
