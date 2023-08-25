from django.urls import path, re_path

from .views import get_languages_view, genres_info_view, GenreProductsListView, SearchProduct


urlpatterns = [
    path('languages/', get_languages_view, name='product_languages_list'),
    path('genres/', genres_info_view, name='product_genres'),
    re_path('^genre/products/(?P<genre_id>.+)/$', GenreProductsListView.as_view(), name='product_genre_products'),
    path('search/', SearchProduct.as_view(), name='product_search')
]
