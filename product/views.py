from collections import OrderedDict

from django.conf import settings
from drf_spectacular.types import OpenApiTypes
from drf_spectacular.utils import extend_schema, OpenApiParameter, extend_schema_view
from rest_framework import generics, status, filters
from rest_framework.response import Response

from currencies.mixins import CurrencyMixin
from rakuten_scraping.tasks import check_product_availability
from users.permissions import RegistrationPayedPermission, EmailConfirmedPermission
from utils.filters import FilterByLookup
from utils.paginators import PagePagination
from utils.views import CachingMixin, LanguageMixin

from .filters import SearchFilterByLang, GenreLevelFilter, PopularProductOrdering, ProductReferenceFilter, FilterByTag, SearchFilterWithTranslating
from .models import Genre, Product, TagGroup, ProductReview
from .paginators import GenrePagination, QuerysetPagination
from .serializers import ProductListSerializer, GenreSerializer, ProductReviewSerializer, ProductRetrieveSerializer, \
    ProductIdsSerializer
from .utils import get_genre_parents_tree

currency_and_lang_params = [settings.LANGUAGE_QUERY_SCHEMA_PARAM, settings.CURRENCY_QUERY_SCHEMA_PARAM]


# -------------------------------------------------- Genres ------------------------------------------------------------
@extend_schema_view(
    get=extend_schema(
        parameters=[
            OpenApiParameter(name='level', type=OpenApiTypes.INT, required=False, default=1),
            settings.LANGUAGE_QUERY_SCHEMA_PARAM
        ]
    )
)
class GenreListView(CachingMixin, LanguageMixin, generics.ListAPIView):
    permission_classes = ()
    authentication_classes = ()
    queryset = Genre.objects.filter(deactivated=False)
    filter_backends = [GenreLevelFilter]
    pagination_class = GenrePagination
    serializer_class = GenreSerializer


@extend_schema_view(get=extend_schema(parameters=[settings.LANGUAGE_QUERY_SCHEMA_PARAM]))
class GenreChildrenView(CachingMixin, LanguageMixin, generics.ListAPIView):
    permission_classes = ()
    authentication_classes = ()
    lookup_field = 'id'
    queryset = Genre.objects.filter(deactivated=False)
    serializer_class = GenreSerializer
    pagination_class = None

    def get_children_list(self):
        genre = self.get_object()
        children = genre.children.filter(deactivated=False)
        return children

    def list(self, request, *args, **kwargs):
        children = self.get_children_list()
        page = self.paginate_queryset(children)
        if page is not None:
            serializer = self.get_serializer(page, many=True)
            return self.get_paginated_response(serializer.data)

        serializer = self.get_serializer(children, many=True)
        return Response(serializer.data)


@extend_schema_view(get=extend_schema(parameters=[settings.LANGUAGE_QUERY_SCHEMA_PARAM]))
class GenreParentsView(CachingMixin, LanguageMixin, generics.ListAPIView):
    permission_classes = ()
    authentication_classes = ()
    lookup_field = 'id'
    queryset = Genre.objects.filter(deactivated=False)
    serializer_class = GenreSerializer

    def list(self, request, *args, **kwargs):
        parents_queryset = self.get_queryset().exclude(level=0).filter(id__in=get_genre_parents_tree(self.get_object()))
        parents = self.filter_queryset(parents_queryset)
        page = self.paginate_queryset(parents)
        if page is not None:
            serializer = self.get_serializer(page, many=True)
            return self.get_paginated_response(serializer.data)

        serializer = self.get_serializer(parents, many=True)
        return Response(serializer.data)


# ------------------------------------------------ Products ------------------------------------------------------------
@extend_schema_view(post=extend_schema(parameters=currency_and_lang_params))
class ProductsByIdsView(CurrencyMixin, LanguageMixin, generics.GenericAPIView):
    permission_classes = ()
    authentication_classes = ()
    queryset = Product.objects.filter(is_active=True)
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


class BaseProductsListView(CurrencyMixin, LanguageMixin, generics.ListAPIView):
    permission_classes = ()
    authentication_classes = ()
    queryset = Product.objects.filter(is_active=True, availability=True)
    pagination_class = PagePagination
    serializer_class = ProductListSerializer
    filter_backends = [SearchFilterByLang, PopularProductOrdering, FilterByTag, filters.OrderingFilter]
    search_fields_ja = ['name', 'description', 'genres__genre__name']
    search_fields_ru = ['name_ru', 'description_ru', 'genres__genre__name_ru']
    search_fields_en = ['name_en', 'description_en', 'genres__genre__name_en']
    search_fields_tr = ['name_tr', 'description_tr', 'genres__genre__name_tr']
    search_fields_ky = ['name_ky', 'description_ky', 'genres__genre__name_ky']
    search_fields_kz = ['name_kz', 'description_kz', 'genres__genre__name_kz']
    ordering_fields = ['created_at', 'price']


@extend_schema_view(get=extend_schema(parameters=currency_and_lang_params))
class ProductsListByGenreView(BaseProductsListView):
    lookup_url_kwarg = 'id'
    lookup_field = 'genres__genre_id'
    filter_backends = (FilterByLookup, *BaseProductsListView.filter_backends)


@extend_schema_view(get=extend_schema(parameters=currency_and_lang_params))
class ProductsListView(BaseProductsListView):
    pagination_class = QuerysetPagination
    filter_backends = [SearchFilterWithTranslating, PopularProductOrdering, FilterByTag, filters.OrderingFilter]
    search_fields = ('name',)

    def get_queryset(self):
        return super().get_queryset().prefetch_related('image_urls')

    def list(self, request, *args, **kwargs):
        queryset = self.filter_queryset(self.get_queryset())
        page_queryset = self.paginate_queryset(queryset)

        sliced_queryset = page_queryset or queryset
        serializer = self.get_serializer(sliced_queryset, many=True)

        data = OrderedDict()
        data['products'] = serializer.data
        base_q = TagGroup.objects.filter(id__in=sliced_queryset.values_list('tags__tag__group_id', flat=True))
        data['tags'] = base_q.tags_list(
            name_field=self.build_translate_field('name'),
            tag_ids=sliced_queryset.values_list('tags__tag_id', flat=True)
        )

        if page_queryset is not None:
            return self.get_paginated_response(data)
        return Response(data)


@extend_schema_view(get=extend_schema(parameters=[settings.LANGUAGE_QUERY_SCHEMA_PARAM]))
class TagByGenreListView(LanguageMixin, generics.ListAPIView):
    permission_classes = ()
    authentication_classes = ()
    queryset = TagGroup.objects.all()
    lookup_url_kwarg = 'id'
    name_field = 'name'

    def get_queryset(self):
        return super().get_queryset().filter(
            tags__producttag__product__genres__genre_id=self.kwargs[self.lookup_url_kwarg]
        ).distinct()

    def get_name_field(self):
        lang = self.get_lang()
        return f'{self.name_field}_{lang}' if lang != 'ja' else self.name_field

    def list(self, request, *args, **kwargs):
        groups = self.get_queryset()
        if not groups.exists():
            return Response(status=status.HTTP_404_NOT_FOUND)
        return Response(groups.tags_list(self.get_name_field()))


@extend_schema_view(get=extend_schema(parameters=currency_and_lang_params))
class ProductRetrieveView(CurrencyMixin, LanguageMixin, generics.RetrieveAPIView):
    permission_classes = ()
    authentication_classes = ()
    lookup_field = 'id'
    queryset = Product.objects.filter(is_active=True)
    serializer_class = ProductRetrieveSerializer

    def retrieve(self, request, *args, **kwargs):
        instance = self.get_object()
        serializer = self.get_serializer(instance)
        check_product_availability.delay(product_id=instance.id)
        return Response(serializer.data)


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
@extend_schema_view(get=extend_schema(parameters=currency_and_lang_params))
class ReferenceListView(CurrencyMixin, LanguageMixin, generics.ListAPIView):
    permission_classes = ()
    authentication_classes = ()
    queryset = Product.objects.filter(is_active=True, availability=True)
    filter_backends = [ProductReferenceFilter]
    serializer_class = ProductListSerializer
    pagination_class = PagePagination
