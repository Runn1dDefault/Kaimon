from django.conf import settings
from drf_spectacular.utils import extend_schema, extend_schema_view
from rest_framework import mixins
from rest_framework.decorators import action
from rest_framework.filters import SearchFilter, OrderingFilter
from rest_framework.generics import ListAPIView
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.viewsets import ReadOnlyModelViewSet, GenericViewSet

from currencies.mixins import CurrencyMixin
from users.permissions import EmailConfirmedPermission, RegistrationPayedPermission, IsAuthor
from utils.filters import ListFilter
from utils.helpers import recursive_single_tree
from utils.views import CachingMixin

from .filters import CategoryLevelFilter, SiteFilter, ProductReferenceFilter
from .models import Category, Product, Tag, ProductReview
from .paginations import CategoryPagination, ProductReviewPagination, ProductPagination
from .serializers import CategorySerializer, ShortProductSerializer, ProductDetailSerializer, ProductReviewSerializer


class CategoryViewSet(CachingMixin, ReadOnlyModelViewSet):
    permission_classes = ()
    authentication_classes = ()
    queryset = Category.objects.filter(deactivated=False)
    serializer_class = CategorySerializer
    pagination_class = CategoryPagination
    lookup_url_kwarg = "category_id"
    lookup_field = "id"
    filter_backends = (SiteFilter, CategoryLevelFilter)

    @action(methods=['GET'], detail=True, url_path='children')
    def children(self, request, **kwargs):
        category = self.get_object()
        queryset = self.filter_queryset(category.children.filter(deactivated=False))
        serializer = self.get_serializer(queryset, many=True)
        return Response(serializer.data)

    @action(methods=['GET'], detail=True, url_path='parents')
    def parents(self, request, **kwargs):
        category = self.get_object()
        category_tree = [category]
        parent_ids = recursive_single_tree(category, 'parent')
        parents = list(self.filter_queryset(self.get_queryset().filter(id__in=parent_ids)))
        category_tree.extend(parents)
        serializer = self.get_serializer(instance=category_tree, many=True)
        return Response(serializer.data)

    @action(methods=['GET'], detail=True, url_path='tags')
    def tags(self, request, category_id):
        tag_groups = Tag.collections.filter(group__isnull=True, products__categories__id=category_id)
        return Response(tag_groups.collected_children())


@extend_schema_view(post=extend_schema(parameters=[settings.CURRENCY_QUERY_SCHEMA_PARAM]))
class ProductsViewSet(CurrencyMixin, ReadOnlyModelViewSet):
    permission_classes = ()
    authentication_classes = ()
    queryset = Product.objects.filter(is_active=True)
    pagination_class = ProductPagination
    serializer_class = ShortProductSerializer
    retrieve_serializer_class = ProductDetailSerializer
    lookup_url_kwarg = "product_id"
    lookup_field = "id"
    filter_backends = (SiteFilter, ListFilter, SearchFilter, OrderingFilter)
    list_filter_fields = {"product_ids": "id", "categories_ids": "categories__id"}
    search_fields = ("name", "categories__name")
    ordering_fields = ("created_at",)

    def get_serializer_class(self):
        if self.detail:
            return self.retrieve_serializer_class
        return self.serializer_class

    @action(methods=['GET'], detail=True, url_path='tags')
    def tags(self, request):
        product = self.get_object()
        tag_groups = Tag.collections.filter(group__isnull=True, products__id=product.id)
        tag_ids = product.tags.values('id', flat=True)
        return Response(tag_groups.collected_children(tag_ids))


class ProductReviewsAPIView(ListAPIView):
    permission_classes = ()
    authentication_classes = ()
    lookup_url_kwarg = "review_id"
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
    mixins.RetrieveModelMixin,
    mixins.DestroyModelMixin,
    mixins.ListModelMixin,
    GenericViewSet
):
    permission_classes = (IsAuthenticated, EmailConfirmedPermission, RegistrationPayedPermission, IsAuthor)
    queryset = ProductReview.objects.all()
    serializer_class = ProductReviewSerializer
    pagination_class = ProductReviewPagination

    def get_queryset(self):
        return super().get_queryset().filter(user=self.request.user)


@extend_schema_view(get=extend_schema(parameters=[settings.CURRENCY_QUERY_SCHEMA_PARAM]))
class ReferenceListAPIView(CachingMixin, CurrencyMixin, ListAPIView):
    permission_classes = ()
    authentication_classes = ()
    queryset = Product.objects.filter(is_active=True)
    filter_backends = [ProductReferenceFilter]
    serializer_class = ShortProductSerializer
    pagination_class = ProductPagination
