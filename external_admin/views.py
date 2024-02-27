from django.db import transaction
from django.utils.translation import gettext_lazy as _
from drf_spectacular.utils import extend_schema
from rest_framework import generics, mixins, viewsets, status, filters, parsers
from rest_framework.decorators import action
from rest_framework.filters import SearchFilter, OrderingFilter
from rest_framework.generics import get_object_or_404
from rest_framework.parsers import MultiPartParser, FormParser, JSONParser
from rest_framework.response import Response

from products.filters import CategoryLevelFilter
from service.models import Conversion
from products.models import Product, ProductReview, Tag, Category, ProductInventory, ProductImage
from promotions.models import Promotion
from service.utils import recursive_single_tree
from users.models import User
from orders.models import Order
from service.mixins import CachingMixin
from service.filters import FilterByFields, DateRangeFilter, ListFilter, SiteFilter

from .mixins import DirectorViewMixin, StaffViewMixin
from .paginators import UserListPagination, AdminPagePagination
from .serializers import (
    ConversionAdminSerializer, PromotionAdminSerializer,
    ProductAdminSerializer, ProductDetailAdminSerializer,
    ProductImageAdminSerializer, UserAdminSerializer, TagAdminSerializer,
    ProductReviewAdminSerializer, OrderAnalyticsSerializer, UserAnalyticsSerializer, ReviewAnalyticsSerializer,
    OrderAdminSerializer, CategoryAdminSerializer, ReceiptAdminSerializer, ProductInventorySerializer,
    BaseOrderAdminSerializer, ProductImageLoaderSerializer
)


# ---------------------------------------------- Users -----------------------------------------------------------------
class UserAdminViewSet(DirectorViewMixin, viewsets.ModelViewSet):
    queryset = User.objects.exclude(username="deleted").filter(role=User.Role.CLIENT)
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
class CategoryAdminViewSet(StaffViewMixin, viewsets.ModelViewSet):
    queryset = Category.objects.filter(level__gt=0)
    serializer_class = CategoryAdminSerializer
    pagination_class = AdminPagePagination
    lookup_url_kwarg = "category_id"
    lookup_field = "id"
    filter_backends = (SearchFilter, SiteFilter, CategoryLevelFilter)
    search_fields = ('id', 'name')

    @extend_schema(responses={status.HTTP_204_NO_CONTENT: None})
    @action(methods=['GET'], detail=True, url_path='change-activity')
    def activate_or_deactivate_genre(self, request, **kwargs):
        category = self.get_object()
        category.deactivated = not category.deactivated
        category.save()
        return Response(status=status.HTTP_204_NO_CONTENT)

    @action(methods=['GET'], detail=True, url_path='children')
    def children(self, request, **kwargs):
        category = self.get_object()
        queryset = self.filter_queryset(category.children.all())
        serializer = self.get_serializer(queryset, many=True)
        return Response(serializer.data)

    @action(methods=['GET'], detail=True, url_path='tree')
    def categories_tree(self, request, **kwargs):
        category = self.get_object()
        category_tree = [category]
        parent_ids = recursive_single_tree(category, 'parent')
        parents = list(self.filter_queryset(self.get_queryset().filter(id__in=parent_ids)))
        category_tree.extend(parents)
        serializer = self.get_serializer(instance=category_tree, many=True)
        return Response(serializer.data)

    @action(methods=['GET'], detail=True, url_path='tags')
    def tags(self, request, **kwargs):
        category = self.get_object()
        return Response(Tag.collections.filter(products__in=category.products.all()).grouped_tags())


# -------------------------------------------------- Tag ---------------------------------------------------------------
class TagGroupAdminViewSet(CachingMixin, StaffViewMixin, generics.ListAPIView):
    queryset = Tag.collections.filter(group__isnull=True)
    filter_backends = (SiteFilter, SearchFilter)
    pagination_class = AdminPagePagination
    serializer_class = TagAdminSerializer
    search_fields = ("name",)

    def list(self, request, *args, **kwargs):
        queryset = self.filter_queryset(self.get_queryset())
        query_ids = queryset.values_list("id", flat=True)
        page = self.paginate_queryset(query_ids)
        queryset = Tag.collections.filter(group_id__in=page)
        return self.get_paginated_response(queryset.grouped_tags())


# ----------------------------------------------- Product --------------------------------------------------------------
class ProductAdminViewSet(StaffViewMixin, viewsets.ModelViewSet):
    queryset = Product.objects.all()
    list_serializer_class = ProductAdminSerializer
    serializer_class = ProductDetailAdminSerializer
    pagination_class = AdminPagePagination
    parser_classes = (parsers.JSONParser, parsers.FormParser, parsers.MultiPartParser)
    lookup_url_kwarg = 'product_id'
    lookup_field = 'id'
    filter_backends = (filters.SearchFilter, SiteFilter, ListFilter)
    search_fields = ('id', 'name', 'categories__name')

    def get_serializer_class(self):
        if self.request.method == 'GET' and self.detail is False:
            return self.list_serializer_class or self.serializer_class
        return self.serializer_class

    def get_queryset(self):
        queryset = super().get_queryset()
        if self.request.method != "GET":
            return queryset

        if self.detail is False:
            queryset = queryset.only("id", "name", "is_active", "avg_rating", "reviews_count")
        else:
            queryset = queryset.only("id", "name", "description", "avg_rating", "reviews_count", "is_active",
                                     "created_at", "can_choose_tags")
        return queryset

    @action(methods=['GET'], detail=True, url_path='tags')
    def tags(self, request, product_id):
        return Response(Tag.collections.filter(products__id=product_id).grouped_tags())

    @extend_schema(responses={status.HTTP_204_NO_CONTENT: None})
    @action(methods=['GET'], detail=True, url_path='change-activity')
    def activate_or_deactivate_product(self, request, **kwargs):
        genre = self.get_object()
        genre.is_active = not genre.is_active
        genre.save()
        return Response(status=status.HTTP_204_NO_CONTENT)

    @extend_schema(responses={status.HTTP_200_OK: None}, request=ProductImageLoaderSerializer)
    @action(methods=['POST'], detail=True, url_path='add-images')
    def add_new_image(self, request, **kwargs):
        product = self.get_object()
        serializer = ProductImageLoaderSerializer(data=request.data, many=False, context=self.get_serializer_context())
        serializer.is_valid(raise_exception=True)
        images = ProductImage.objects.bulk_create(
            [ProductImage(product=product, image=image) for image in serializer.validated_data['images']]
        )
        return Response(
            ProductImageAdminSerializer(instance=images, many=True, context=self.get_serializer_context()).data,
            status=status.HTTP_200_OK
        )

    @extend_schema(responses={status.HTTP_204_NO_CONTENT: None})
    @action(
        methods=['DELETE'],
        detail=True,
        url_path='remove-image/(?P<image_id>.+)'
    )
    def remove_image(self, request, product_id, image_id):
        image = get_object_or_404(ProductImage.objects.filter(product_id=product_id), id=image_id)
        image.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)

    @extend_schema(responses={status.HTTP_204_NO_CONTENT: None, status.HTTP_404_NOT_FOUND: None})
    @action(
        methods=['DELETE'],
        detail=True,
        url_path=r'remove-tag/(?P<tag_id>.+)'
    )
    def remove_tag(self, request, **kwargs):
        tag = get_object_or_404(self.get_object().tags.all(), id=kwargs['tag_id'])
        tag.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)

    @extend_schema(responses={status.HTTP_200_OK: TagAdminSerializer, status.HTTP_404_NOT_FOUND: None})
    @action(
        methods=['GET'],
        detail=True,
        url_path=r'add-tag/(?P<tag_id>.+)'
    )
    def add_tag(self, request, **kwargs):
        tag_id = kwargs['tag_id']
        if not Tag.objects.filter(id=tag_id).exists():
            return Response(
                {'detail': _('Tag does with id %s not exist!') % tag_id},
                status=status.HTTP_400_BAD_REQUEST
            )
        product = self.get_object()
        product.tags.add(tag_id)
        serializer = TagAdminSerializer(
            instance=product.tags.get(id=tag_id),
            many=False,
            context=self.get_serializer_context()
        )
        return Response(serializer.data, status=status.HTTP_200_OK)

    @extend_schema(
        responses={status.HTTP_200_OK: CategoryAdminSerializer(many=True), status.HTTP_404_NOT_FOUND: None},
        request=None
    )
    @action(
        methods=['PATCH'],
        detail=True,
        url_path=r'change-category/(?P<category_id>.+)'
    )
    def change_category(self, request, **kwargs):
        product = self.get_object()
        category = get_object_or_404(Category.objects.all(), id=kwargs['category_id'])
        categories_tree = recursive_single_tree(category, "parent")
        product.categories.clear()
        product.categories.add(*categories_tree)
        serializer = CategoryAdminSerializer(
            instance=product.categories.all(),
            many=True,
            context=self.get_serializer_context()
        )
        return Response(serializer.data, status=status.HTTP_200_OK)

    @extend_schema(responses={status.HTTP_200_OK: ProductInventorySerializer(many=True)}, request=None)
    @action(methods=['GET'], detail=True, url_path='inventories')
    def get_inventories(self, request, product_id):
        inventories = ProductInventory.objects.filter(product_id=product_id)
        serializer = ProductInventorySerializer(instance=inventories, many=True, context=self.get_serializer_context())
        return Response(serializer.data)

    @extend_schema(responses={status.HTTP_201_CREATED: ProductInventorySerializer(many=False)},
                   request=ProductInventorySerializer(many=False))
    @action(methods=['POST'], detail=False, url_path='inventories')
    def create_inventories(self, request, product_id):
        serializer = ProductInventorySerializer(data=request.data, many=False, context=self.get_serializer_context())
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response(serializer.data, status=status.HTTP_201_CREATED)


class ProductInventoryViewSet(StaffViewMixin, mixins.CreateModelMixin, mixins.UpdateModelMixin,
                              mixins.DestroyModelMixin, viewsets.GenericViewSet):
    queryset = ProductInventory.objects.all()
    serializer_class = ProductInventorySerializer


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
    filter_fields = {'moderated': {'db_field': 'moderated', 'type': 'boolean'}}
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

    @action(methods=['GET'], detail=False, url_path='count')
    def new_count(self, request, **kwargs):
        queryset = self.filter_queryset(self.get_queryset())
        return Response({'count': queryset.count()})


# ---------------------------------------------- Order -----------------------------------------------------------------
class OrderAdminViewSet(StaffViewMixin, mixins.RetrieveModelMixin, mixins.UpdateModelMixin,
                        mixins.ListModelMixin, viewsets.GenericViewSet):
    queryset = Order.objects.all()
    list_serializer_class = BaseOrderAdminSerializer
    serializer_class = OrderAdminSerializer
    pagination_class = AdminPagePagination
    lookup_field = 'id'
    lookup_url_kwarg = 'order_id'
    filter_backends = (SearchFilter, ListFilter, OrderingFilter, DateRangeFilter)
    search_fields = ('customer__email', 'customer__name', 'customer__bayer_code')
    list_filter_fields = {'status': 'status'}
    ordering_fields = ('id', 'created_at', 'modified_at')
    start_param, end_param = 'start_date', 'end_date'
    start_field, end_field = 'created_at__date', 'created_at__date'

    def get_serializer_class(self):
        if self.detail is False and self.request.method == 'GET':
            return self.list_serializer_class
        return self.serializer_class

    @extend_schema(responses={status.HTTP_200_OK: BaseOrderAdminSerializer(many=True)})
    def list(self, request, *args, **kwargs):
        return super().list(request, *args, **kwargs)

    @action(methods=['GET'], detail=False, url_path='new-count')
    def new_count(self, request, **kwargs):
        queryset = self.get_queryset().filter(status=Order.Status.pending)
        return Response({'count': queryset.count()})

    @extend_schema(
        request=ReceiptAdminSerializer,
        responses={status.HTTP_200_OK: ReceiptAdminSerializer, status.HTTP_404_NOT_FOUND: None}
    )
    @action(methods=['PATCH'], detail=True, url_path='update-receipt/(?P<receipt_id>.+)')
    def update_receipt(self, request, **kwargs):
        order = self.get_object()
        receipt = get_object_or_404(order.receipts.all(), id=kwargs['receipt_id'])
        serializer = ReceiptAdminSerializer(
            instance=receipt,
            data=request.data,
            partial=True,
            many=False,
            context=self.get_serializer_context()
        )
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response(serializer.data, status=status.HTTP_200_OK)

    @extend_schema(
        request=ReceiptAdminSerializer,
        responses={status.HTTP_200_OK: ReceiptAdminSerializer}
    )
    @action(methods=['POST'], detail=False, url_path='add-receipt')
    def add_receipt(self, request, **kwargs):
        serializer = ReceiptAdminSerializer(
            data=request.data,
            many=False,
            context=self.get_serializer_context()
        )
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response(serializer.data, status=status.HTTP_200_OK)

    @extend_schema(request=None, responses={status.HTTP_204_NO_CONTENT: None})
    @action(methods=['DELETE'], detail=True, url_path='remove-receipt/(?P<receipt_id>.+)')
    def remove_receipt(self, request, **kwargs):
        order = self.get_object()
        receipt = get_object_or_404(order.receipts.all(), kwargs['receipt_id'])
        receipt.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)


# ----------------------------------------------- Promotions -----------------------------------------------------------
class PromotionAdminViewSet(StaffViewMixin, viewsets.ModelViewSet):
    queryset = Promotion.objects.all()
    pagination_class = AdminPagePagination
    serializer_class = PromotionAdminSerializer
    parser_classes = (MultiPartParser, FormParser, JSONParser)
    lookup_field = 'id'
    lookup_url_kwarg = 'promotion_id'
    filter_backends = (FilterByFields, SearchFilter, SiteFilter, OrderingFilter)
    filter_fields = {'deactivated': {'db_field': 'deactivated', 'type': 'boolean'}}
    search_fields = ('id', 'banner__name',)
    ordering_fields = ('id', 'created_at',)

    def perform_create(self, serializer):
        with transaction.atomic():
            super().perform_create(serializer)

    def perform_update(self, serializer):
        with transaction.atomic():
            super().perform_update(serializer)

    @extend_schema(responses={status.HTTP_204_NO_CONTENT: None})
    @action(methods=['GET'], detail=True, url_path='change-activity')
    def deactivate_or_activate(self, request, **kwargs):
        promotion = self.get_object()
        promotion.deactivated = not promotion.deactivated
        promotion.save()
        return Response(status=status.HTTP_204_NO_CONTENT)

    @extend_schema(responses={status.HTTP_200_OK: None, status.HTTP_404_NOT_FOUND: None}, request=None)
    @action(methods=['PATCH'], detail=True, url_path="add-product/(?P<product_id>.+)")
    def add_product(self, request, **kwargs):
        promotion = self.get_object()
        product = get_object_or_404(Product.objects.all(), id=kwargs['product_id'])
        promotion.products.add(product)
        return Response(status=status.HTTP_200_OK)

    @extend_schema(responses={status.HTTP_204_NO_CONTENT: None, status.HTTP_404_NOT_FOUND: None}, request=None)
    @action(methods=['DELETE'], detail=True, url_path="remove-product/(?P<product_id>.+)")
    def remove_product(self, request, **kwargs):
        promotion = self.get_object()
        product = get_object_or_404(Product.objects.all(), id=kwargs['product_id'])
        promotion.products.remove(product)
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
    filter_backends = (OrderingFilter,)
    ordering_fields = ('currency_from',)
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
