from django.conf import settings
from django.db.models import Subquery
from django.utils.decorators import method_decorator
from django.views.decorators.cache import cache_page
from drf_spectacular.utils import extend_schema
from rest_framework import mixins
from rest_framework.decorators import action
from rest_framework.filters import SearchFilter, OrderingFilter
from rest_framework.generics import ListAPIView
from rest_framework.permissions import IsAuthenticated, AllowAny
from rest_framework.response import Response
from rest_framework.viewsets import ReadOnlyModelViewSet, GenericViewSet

from users.permissions import EmailConfirmedPermission, RegistrationPayedPermission, IsAuthor
from service.mixins import CurrencyMixin, CachingMixin
from service.filters import ListFilter, SiteFilter
from service.utils import recursive_single_tree

from .filters import CategoryLevelFilter, ProductReferenceFilter, ProductTagFilter
from .models import Category, Product, Tag, ProductReview
from .paginations import CategoryPagination, ProductReviewPagination, ProductPagination
from .serializers import (
    CategorySerializer,
    ShortProductSerializer, ProductDetailSerializer, ProductReferenceSerializer, ProductReviewSerializer
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

    @method_decorator(cache_page(timeout=settings.PAGE_CACHED_SECONDS, cache='pages_cache',
                                 key_prefix='category_tags'))
    @action(methods=['GET'], detail=True, url_path='tags')
    def tags(self, request, **kwargs):
        category = self.get_object()
        return Response(
            Tag.collections.filter(products__in=category.products.all()).grouped_tags()
        )


class ProductsViewSet(CachingMixin, CurrencyMixin, ReadOnlyModelViewSet):
    permission_classes = (AllowAny,)
    queryset = Product.objects.filter(is_active=True)
    pagination_class = ProductPagination
    serializer_class = ShortProductSerializer
    retrieve_serializer_class = ProductDetailSerializer
    lookup_url_kwarg = "product_id"
    lookup_field = "id"
    filter_backends = (SiteFilter, ListFilter, ProductTagFilter, ProductReferenceFilter, SearchFilter, OrderingFilter)
    list_filter_fields = {"product_ids": "id", "category_ids": "categories__id"}
    search_fields = ("name", "categories__name")
    ordering_fields = ("created_at",)

    @classmethod
    def get_cache_prefix(cls) -> str:
        return "product"

    @extend_schema(parameters=[settings.CURRENCY_QUERY_SCHEMA_PARAM])
    def list(self, request, *args, **kwargs):
        return super().list(request, *args, **kwargs)

    @extend_schema(parameters=[settings.CURRENCY_QUERY_SCHEMA_PARAM])
    def retrieve(self, request, *args, **kwargs):
        return super().retrieve(request, *args, **kwargs)

    def get_serializer_class(self):
        if self.detail:
            return self.retrieve_serializer_class
        return self.serializer_class

    @method_decorator(cache_page(timeout=settings.PAGE_CACHED_SECONDS, cache='pages_cache',
                                 key_prefix='product_tags'))
    @action(methods=['GET'], detail=True, url_path='tags')
    def tags(self, request, product_id):
        product = self.get_object()
        return Response(
            Tag.collections.filter(products__id=product_id)
                           .grouped_tags(product.tags.values_list('id', flat=True))
        )

    @method_decorator(cache_page(timeout=settings.PAGE_CACHED_SECONDS, cache='pages_cache',
                                 key_prefix='product_reference'))
    @extend_schema(request=ProductReferenceSerializer)
    @action(methods=['POST'], detail=True, url_path='reference')
    def get_reference(self, request, product_id):
        reference_serializer = ProductReferenceSerializer(data=request.data, many=False)
        reference_serializer.is_valid(raise_exception=True)
        req_data = reference_serializer.validated_data
        category = Subquery(Category.objects.filter(products__id=product_id).order_by('-level').values('id')[:1])
        queryset = self.filter_queryset(self.get_queryset())
        exclude_ids = (product_id, *req_data.get('exclude', []))
        reference_queryset = (
            queryset.exclude(id__in=exclude_ids).filter(categories__id=category)
                    .order_by('-site_reviews_count', '-site_avg_rating')
        )
        page = self.paginate_queryset(reference_queryset)
        data = self.serializer_class(instance=page, many=True, context=self.get_serializer_context()).data
        return self.get_paginated_response(data)


class ProductReviewsAPIView(ListAPIView):
    permission_classes = (AllowAny,)
    lookup_url_kwarg = "product_id"
    lookup_field = 'id'
    queryset = Product.objects.filter(is_active=True)
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
    queryset = ProductReview.objects.filter(moderated=True)
    serializer_class = ProductReviewSerializer
    pagination_class = ProductReviewPagination

    def get_queryset(self):
        return super().get_queryset().filter(user=self.request.user)
