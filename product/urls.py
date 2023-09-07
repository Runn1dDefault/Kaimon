from django.urls import path, re_path

from .views import (
    get_languages_view,
    GenreListView, GenreChildrenView, GenreParentsView, TagByGenreListView,
    ProductsListByGenreView, SearchProductView, ProductRetrieveView,
    ProductReviewCreateView, ProductReviewListView,
    ReferenceListView,
)

genres_urlpatterns = [
    path('genres/', GenreListView.as_view(), name='product_genre_list'),
    re_path('^genres/(?P<id>.+)/children/$', GenreChildrenView.as_view(), name='product_genre_children_list'),
    re_path('^genres/(?P<id>.+)/parents/$', GenreParentsView.as_view(), name='product_genre_parents_list'),
    re_path('^genres/(?P<id>.+)/tags/$', TagByGenreListView.as_view(), name='product_genre_tags_list'),
]

reviews_urlpatterns = [
    path('review/', ProductReviewCreateView.as_view(), name='product_review_create'),
    re_path('^(?P<id>.+)/reviews/', ProductReviewListView.as_view(), name='product_review_list'),
]

products_urlpatterns = [
    re_path('^genres/(?P<id>.+)/products/$', ProductsListByGenreView.as_view(), name='product_list'),
    path('search/', SearchProductView.as_view(), name='product_search'),
    # Important: product_detail must always be the last, otherwise it will overlap other addresses.
    # also product_urlpatterns should also be at the end of urlpatterns
    re_path('^(?P<id>.+)/$', ProductRetrieveView.as_view(), name='product_detail'),
]

additions_urlpatterns = [
    path('languages/', get_languages_view, name='product_languages_list'),
    path('recommendations/', ReferenceListView.as_view(), name='product_recommendations_list'),
]

urlpatterns = additions_urlpatterns + genres_urlpatterns + reviews_urlpatterns + products_urlpatterns
