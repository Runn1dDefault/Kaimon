from django.conf import settings
from drf_spectacular.types import OpenApiTypes
from drf_spectacular.utils import extend_schema, OpenApiParameter, extend_schema_view
from rest_framework import generics, status, filters
from rest_framework.decorators import api_view
from rest_framework.response import Response

from currencies.mixins import CurrencyMixin
from users.permissions import RegistrationPayedPermission, EmailConfirmedPermission
from utils.helpers import recursive_single_tree
from utils.paginators import PagePagination
from utils.views import CachingMixin

from .filters import FilterBySite, GenreLevelFilter, PopularProductOrdering, ProductReferenceFilter, FilterByTag
from .models import Genre, Product, TagGroup, ProductReview
from .paginators import GenrePagination
from .serializers import ProductListSerializer, GenreSerializer, ProductReviewSerializer, ProductRetrieveSerializer, \
    ProductIdsSerializer
from .utils import get_tags_for_product


# -------------------------------------------------- Genres ------------------------------------------------------------
@extend_schema_view(
    get=extend_schema(
        parameters=[OpenApiParameter(name='level', type=OpenApiTypes.INT, required=False, default=1)]
    )
)
class GenreListView(CachingMixin, generics.ListAPIView):
    permission_classes = ()
    authentication_classes = ()
    queryset = Genre.objects.filter(deactivated=False)
    filter_backends = (GenreLevelFilter, FilterBySite)
    pagination_class = GenrePagination
    serializer_class = GenreSerializer


class GenreChildrenView(CachingMixin, generics.ListAPIView):
    permission_classes = ()
    authentication_classes = ()
    filter_backends = (FilterBySite,)
    lookup_field = 'id'
    queryset = Genre.objects.filter(deactivated=False)
    serializer_class = GenreSerializer
    pagination_class = None

    def get_children_list(self):
        return self.get_object().children.filter(deactivated=False)

    def list(self, request, *args, **kwargs):
        serializer = self.get_serializer(self.get_children_list(), many=True)
        return Response(serializer.data)


class GenreParentsView(CachingMixin, generics.ListAPIView):
    permission_classes = ()
    authentication_classes = ()
    filter_backends = (FilterBySite,)
    lookup_field = 'id'
    queryset = Genre.objects.filter(level__gt=0, deactivated=False)
    serializer_class = GenreSerializer

    def list(self, request, *args, **kwargs):
        current_genre = self.get_object()
        genres = [current_genre]
        parent_ids = recursive_single_tree(current_genre, 'parent')
        parents = list(self.filter_queryset(self.get_queryset().filter(id__in=parent_ids)))
        genres.extend(parents)
        serializer = self.get_serializer(instance=genres, many=True)
        return Response(serializer.data)


# ------------------------------------------------ Products ------------------------------------------------------------
@extend_schema_view(post=extend_schema(parameters=[settings.CURRENCY_QUERY_SCHEMA_PARAM]))
class ProductsByIdsView(CurrencyMixin, generics.GenericAPIView):
    permission_classes = ()
    authentication_classes = ()
    queryset = Product.objects.filter(is_active=True)
    filter_backends = (FilterBySite,)
    pagination_class = PagePagination
    serializer_class = ProductIdsSerializer
    list_serializer_class = ProductRetrieveSerializer

    def get_serializer(self, *args, **kwargs):
        kwargs.setdefault('context', self.get_serializer_context())
        if kwargs.get('instance') is not None and kwargs.get('many') is True:
            serializer_class = self.list_serializer_class
        else:
            serializer_class = self.get_serializer_class()
        return serializer_class(*args, **kwargs)

    def list(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data, many=False)
        serializer.is_valid(raise_exception=True)
        products = serializer.validated_data['product_ids']
        if products:
            list_serializer = self.get_serializer(instance=products, many=True)
            return Response(list_serializer.data)
        return Response(status=status.HTTP_404_NOT_FOUND)

    def post(self, request, *args, **kwargs):
        return self.list(request, *args, **kwargs)


@extend_schema_view(get=extend_schema(parameters=[settings.CURRENCY_QUERY_SCHEMA_PARAM]))
class ProductsListView(CurrencyMixin, generics.ListAPIView):
    permission_classes = ()
    authentication_classes = ()
    queryset = Product.objects.filter(is_active=True, availability=True)
    pagination_class = PagePagination
    serializer_class = ProductRetrieveSerializer
    filter_backends = (FilterBySite, filters.SearchFilter, PopularProductOrdering, FilterByTag, filters.OrderingFilter)
    search_fields = ['name', 'genres__name']
    ordering_fields = ['created_at']


@extend_schema_view(get=extend_schema(parameters=[settings.CURRENCY_QUERY_SCHEMA_PARAM]))
class ProductsListByGenreView(ProductsListView):
    lookup_url_kwarg = 'id'
    lookup_field = 'genres__id'
    filter_backends = (FilterBySite,)

    def get_lookup_kwargs(self):
        return {self.lookup_field: self.kwargs[self.lookup_url_kwarg]}

    def get_queryset(self):
        return super().get_queryset().filter(**self.get_lookup_kwargs())


class TagByGenreListView(generics.ListAPIView):
    permission_classes = ()
    authentication_classes = ()
    filter_backends = (FilterBySite,)
    queryset = TagGroup.objects.all()
    lookup_url_kwarg = 'id'
    name_field = 'name'

    def get_queryset(self):
        return super().get_queryset().filter(
            tags__products__genres__id=self.kwargs[self.lookup_url_kwarg]
        ).distinct()

    def list(self, request, *args, **kwargs):
        groups = self.filter_queryset(self.get_queryset())
        if not groups.exists():
            return Response(status=status.HTTP_404_NOT_FOUND)
        return Response(groups.tags_list())


@extend_schema_view(get=extend_schema(parameters=[settings.CURRENCY_QUERY_SCHEMA_PARAM]))
class ProductRetrieveView(CurrencyMixin, generics.RetrieveAPIView):
    permission_classes = ()
    authentication_classes = ()
    filter_backends = (FilterBySite,)
    lookup_field = 'id'
    queryset = Product.objects.filter(is_active=True)
    serializer_class = ProductRetrieveSerializer

    def retrieve(self, request, *args, **kwargs):
        instance = self.get_object()
        serializer = self.get_serializer(instance)
        # check_product_availability.delay(product_id=instance.id)
        return Response(serializer.data)


@api_view(['GET'])
def product_tags_info_view(request, site, product_id):
    return Response(get_tags_for_product(site, product_id))


# ------------------------------------------------- Reviews ------------------------------------------------------------
class UserReviewListView(generics.ListAPIView):
    permission_classes = [EmailConfirmedPermission, RegistrationPayedPermission]
    pagination_class = PagePagination
    queryset = ProductReview.objects.filter(is_active=True)
    serializer_class = ProductReviewSerializer

    def get_queryset(self):
        return super().get_queryset().filter(user=self.request.user)


class ProductReviewCreateView(generics.CreateAPIView):
    serializer_class = ProductReviewSerializer
    permission_classes = [EmailConfirmedPermission, RegistrationPayedPermission]


class ProductReviewDestroyView(generics.DestroyAPIView):
    lookup_field = 'id'
    queryset = Product.objects.filter(is_active=True)
    serializer_class = ProductReviewSerializer
    permission_classes = [EmailConfirmedPermission, RegistrationPayedPermission]

    def get_queryset(self):
        return self.request.user.reviews.all()


class ProductReviewListView(generics.ListAPIView):
    permission_classes = ()
    authentication_classes = ()
    lookup_field = 'id'
    queryset = Product.objects.filter(is_active=True)
    serializer_class = ProductReviewSerializer
    pagination_class = PagePagination

    def list(self, request, *args, **kwargs):
        product = self.get_object()
        queryset = self.filter_queryset(product.reviews.filter(is_active=True))

        page = self.paginate_queryset(queryset)
        if page is not None:
            serializer = self.get_serializer(page, many=True)
            return self.get_paginated_response(serializer.data)

        serializer = self.get_serializer(queryset, many=True)
        return Response(serializer.data)


# -------------------------------------------- Recommendations ---------------------------------------------------------
@extend_schema_view(get=extend_schema(parameters=[settings.CURRENCY_QUERY_SCHEMA_PARAM]))
class ReferenceListView(CurrencyMixin, generics.ListAPIView):
    permission_classes = ()
    authentication_classes = ()
    queryset = Product.objects.filter(is_active=True, availability=True)
    filter_backends = [ProductReferenceFilter]
    serializer_class = ProductListSerializer
    pagination_class = PagePagination
