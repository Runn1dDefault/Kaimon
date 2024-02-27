from django.conf import settings
from django.db.models import Subquery
from django.utils.decorators import method_decorator
from django.views.decorators.cache import cache_page
from drf_spectacular.types import OpenApiTypes
from drf_spectacular.utils import extend_schema, OpenApiParameter
from rest_framework import mixins
from rest_framework.decorators import action
from rest_framework.filters import SearchFilter, OrderingFilter
from rest_framework.generics import ListAPIView, GenericAPIView
from rest_framework.permissions import IsAuthenticated, AllowAny
from rest_framework.response import Response
from rest_framework.viewsets import ReadOnlyModelViewSet, GenericViewSet

from users.permissions import EmailConfirmedPermission, RegistrationPayedPermission, IsAuthor
from service.mixins import CurrencyMixin, CachingMixin
from service.filters import SiteFilter
from service.utils import recursive_single_tree

from .filters import (
    CategoryLevelFilter, ProductFilter,
    ProductSQLPopularFilter, ProductSQLSearchFilter, ProductSQLNewFilter, ProductsByCategorySQLFilter,
    ProductsByIdsSQlFilter, FilterByIds
)
from .models import Category, Product, Tag, ProductReview, ProductInventory
from .paginations import CategoryPagination, ProductReviewPagination, ProductPagination
from .serializers import (
    CategorySerializer,
    ShortProductSerializer, ProductDetailSerializer, ProductReferenceSerializer, ProductReviewSerializer,
    ProductInventorySerializer
)


class CategoryViewSet(CachingMixin, ReadOnlyModelViewSet):
    permission_classes = (AllowAny,)
    queryset = Category.objects.filter(level__gt=0, deactivated=False)
    serializer_class = CategorySerializer
    pagination_class = CategoryPagination
    lookup_url_kwarg = "category_id"
    lookup_field = "id"
    filter_backends = (SearchFilter, SiteFilter, CategoryLevelFilter)
    search_fields = ('id', 'name')

    @classmethod
    def get_cache_prefix(cls) -> str:
        return "category"

    @method_decorator(cache_page(timeout=settings.PAGE_CACHED_SECONDS, cache='pages_cache',
                                 key_prefix='category_children'))
    @action(methods=['GET'], detail=True, url_path='children')
    def children(self, request, **kwargs):
        category = self.get_object()
        queryset = self.filter_queryset(category.children.filter(deactivated=False))
        serializer = self.get_serializer(queryset, many=True)
        return Response(serializer.data)

    @method_decorator(cache_page(timeout=settings.PAGE_CACHED_SECONDS, cache='pages_cache',
                                 key_prefix='category_tree'))
    @action(methods=['GET'], detail=True, url_path='tree')
    def categories_tree(self, request, **kwargs):
        category = self.get_object()
        category_tree = [category]
        parent_ids = recursive_single_tree(category, 'parent')
        parents = list(self.filter_queryset(self.get_queryset().filter(id__in=parent_ids)))
        category_tree.extend(parents)
        serializer = self.get_serializer(instance=category_tree, many=True)
        return Response(serializer.data)


class ProductsViewSet(CurrencyMixin, CachingMixin, ReadOnlyModelViewSet):
    queryset = Product.objects.filter(is_active=True)
    serializer_class = ShortProductSerializer
    retrieve_serializer_class = ProductDetailSerializer
    pagination_class = ProductPagination
    permission_classes = (AllowAny,)
    lookup_url_kwarg = "product_id"
    lookup_field = "id"
    filter_backends = (SiteFilter, OrderingFilter, ProductFilter)
    ordering_fields = ("created_at",)

    @classmethod
    def get_cache_prefix(cls) -> str:
        return "product"

    def get_serializer_class(self):
        if self.request.method == 'GET' and self.lookup_url_kwarg in self.kwargs:
            return self.retrieve_serializer_class
        return self.serializer_class

    @extend_schema(parameters=[settings.CURRENCY_QUERY_SCHEMA_PARAM])
    def list(self, request, *args, **kwargs):
        return super().list(request, *args, **kwargs)

    @extend_schema(parameters=[settings.CURRENCY_QUERY_SCHEMA_PARAM])
    def retrieve(self, request, *args, **kwargs):
        return super().retrieve(request, *args, **kwargs)

    @method_decorator(cache_page(timeout=settings.PAGE_CACHED_SECONDS, cache='pages_cache',
                                 key_prefix='product_tags'))
    @extend_schema(
        parameters=[
            OpenApiParameter(
                name="inventory_id",
                type=OpenApiTypes.STR,
                required=False
            )
        ]
    )
    @action(methods=['GET'], detail=True, url_path='tags')
    def get_tags(self, request, product_id):
        inventory_id = request.query_params.get("inventory_id")

        if inventory_id:
            return Response(
                Tag.collections.filter(product_inventories__id=inventory_id).grouped_tags()
            )
        return Response(Tag.collections.filter(product_inventories__product_id=product_id).grouped_tags())


class ProductByCategoryView(CachingMixin, CurrencyMixin, ListAPIView):
    queryset = Product.objects.filter(is_active=True)
    serializer_class = ShortProductSerializer
    permission_classes = (AllowAny,)
    filter_backends = (ProductsByCategorySQLFilter,)
    lookup_url_kwarg = 'category_id'

    @classmethod
    def get_cache_prefix(cls) -> str:
        return 'product'


class ProductByIdsView(CurrencyMixin, ListAPIView):
    queryset = Product.objects.filter(is_active=True)
    serializer_class = ShortProductSerializer
    permission_classes = (AllowAny,)
    filter_backends = (ProductsByIdsSQlFilter,)


class ProductReferenceView(CachingMixin, CurrencyMixin, GenericAPIView):
    queryset = Product.objects.filter(is_active=True)
    serializer_class = ShortProductSerializer
    reference_serializer_class = ProductReferenceSerializer
    pagination_class = ProductPagination
    permission_classes = (AllowAny,)
    lookup_url_kwarg = "product_id"
    lookup_field = "id"
    filter_backends = (SiteFilter, ProductFilter)

    @classmethod
    def get_cache_prefix(cls) -> str:
        return 'product'

    def get_reference_serializer(self, *args, **kwargs):
        kwargs.setdefault('context', self.get_serializer_context())
        return self.reference_serializer_class(*args, **kwargs)

    def get_reference_data(self):
        reference_serializer = self.get_reference_serializer(data=self.request.data)
        reference_serializer.is_valid(raise_exception=True)
        return reference_serializer.validated_data

    def get_queryset(self):
        queryset = super().get_queryset()
        reference_data = self.get_reference_data()
        product_id = self.kwargs[self.lookup_url_kwarg]
        exclude_ids = (product_id, *reference_data.get('exclude', []))
        category = Subquery(Category.objects.filter(products__id=product_id).order_by('-level').values('id')[:1])
        return queryset.exclude(id__in=exclude_ids).filter(categories__id=category)

    def post(self, request, *args, **kwargs):
        queryset = self.filter_queryset(self.get_queryset())
        page = self.paginate_queryset(queryset)
        serializer = self.get_serializer(page, many=True)
        return self.get_paginated_response(serializer.data)


class ProductsSearchView(CachingMixin, CurrencyMixin, ListAPIView):
    queryset = Product.objects.filter(is_active=True)
    serializer_class = ShortProductSerializer
    permission_classes = (AllowAny,)
    filter_backends = (ProductSQLSearchFilter,)

    @classmethod
    def get_cache_prefix(cls) -> str:
        return 'product'


class NewProductsView(CachingMixin, CurrencyMixin, ListAPIView):
    queryset = Product.objects.filter(is_active=True)
    serializer_class = ShortProductSerializer
    permission_classes = (AllowAny,)
    filter_backends = (ProductSQLNewFilter,)

    @classmethod
    def get_cache_prefix(cls) -> str:
        return 'product'


class PopularProductsView(CachingMixin, CurrencyMixin, ListAPIView):
    queryset = Product.objects.filter(is_active=True)
    serializer_class = ShortProductSerializer
    permission_classes = (AllowAny,)
    filter_backends = (ProductSQLPopularFilter,)

    @classmethod
    def get_cache_prefix(cls) -> str:
        return 'product'


class ProductReviewsAPIView(ListAPIView):
    permission_classes = (AllowAny,)
    lookup_url_kwarg = "product_id"
    lookup_field = 'id'
    queryset = Product.objects.all()
    serializer_class = ProductReviewSerializer
    pagination_class = ProductReviewPagination

    def list(self, request, *args, **kwargs):
        product = self.get_object()
        queryset = self.filter_queryset(product.reviews.filter(moderated=True))

        page = self.paginate_queryset(queryset)
        if page is not None:
            serializer = self.get_serializer(page, many=True)
            return self.get_paginated_response(serializer.data)

        serializer = self.get_serializer(queryset, many=True)
        return Response(serializer.data)


class UserReviewViewSet(
    mixins.CreateModelMixin,
    mixins.DestroyModelMixin,
    mixins.ListModelMixin,
    GenericViewSet
):
    permission_classes = (IsAuthenticated, EmailConfirmedPermission, RegistrationPayedPermission, IsAuthor)
    queryset = ProductReview.objects.filter(moderated=True).only("id", "rating", "comment", "created_at")
    serializer_class = ProductReviewSerializer
    pagination_class = ProductReviewPagination

    def get_queryset(self):
        return super().get_queryset().filter(user=self.request.user)


class InventoriesByIdsView(CachingMixin, CurrencyMixin, ListAPIView):
    permission_classes = (AllowAny,)
    queryset = ProductInventory.objects.filter(product__is_active=True)
    filter_backends = (FilterByIds,)
    serializer_class = ProductInventorySerializer

    @classmethod
    def get_cache_prefix(cls) -> str:
        return 'product'

    def get_serializer(self, *args, **kwargs):
        kwargs.setdefault("include_products", True)
        return super().get_serializer(*args, **kwargs)
