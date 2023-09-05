from django.urls import path, re_path

from .views import (
    get_languages_view,
    GenreListView, GenreChildrenView, GenreParentsView,
    ProductsListByGenreView, SearchProductView, ProductRetrieveView,
    ProductReviewCreateView, ProductReviewListView
)


urlpatterns = [
    path('languages/', get_languages_view, name='product_languages_list'),
    # Genres
    path('genres/', GenreListView.as_view(), name='product_genre_list'),
    re_path('^genres/(?P<id>.+)/children/$', GenreChildrenView.as_view(), name='product_genre_children_list'),
    re_path('^genres/(?P<id>.+)/parents/$', GenreParentsView.as_view(), name='product_genre_children_list'),
    # Products
    re_path('^genres/(?P<id>.+)/products/$', ProductsListByGenreView.as_view(), name='product_list'),
    re_path('^/(?P<id>.+)/$', ProductRetrieveView.as_view(), name='product_retrieve'),
    path('search/', SearchProductView.as_view(), name='product_search'),
    # Reviews
    path('review/', ProductReviewCreateView.as_view(), name='product_review_create'),
    re_path('^(?P<id>.+)/reviews/', ProductReviewListView.as_view(), name='product_review_list'),

]
