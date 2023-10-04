from django.urls import path, re_path

from .views import (
    GenreListView, GenreChildrenView, GenreParentsView, TagByGenreListView,
    ProductsByIdsView, ProductsListByGenreView, ProductRetrieveView, ProductReviewDestroyView,
    UserReviewListView, ProductReviewCreateView, ProductReviewListView,
    ReferenceListView
)

genres_urlpatterns = [
    path('genres/', GenreListView.as_view(), name='product-genre-list'),
    re_path('^genres/(?P<id>.+)/children/$', GenreChildrenView.as_view(), name='product-genre-children-list'),
    re_path('^genres/(?P<id>.+)/parents/$', GenreParentsView.as_view(), name='product-genre-parents-list'),
    re_path('^genres/(?P<id>.+)/tags/$', TagByGenreListView.as_view(), name='product-genre-tags-list'),
]

reviews_urlpatterns = [
    path('my-reviews/', UserReviewListView.as_view(), name='product-user-reviews-list'),
    path('reviews/', ProductReviewCreateView.as_view(), name='product-review-create'),
    re_path('^(?P<id>.+)/reviews/', ProductReviewListView.as_view(), name='product-review-list'),
    re_path('^reviews/(?P<id>.+)/$', ProductReviewDestroyView.as_view(), name='product-review-delete'),
]

additions_urlpatterns = [
    path('recommendations/', ReferenceListView.as_view(), name='product-recommendations-list'),
]

products_urlpatterns = [
    re_path('^products-by-ids/$', ProductsByIdsView.as_view(), name='product-by-ids-list'),
    re_path('^genres/(?P<id>.+)/products/$', ProductsListByGenreView.as_view(), name='product-list'),
    # Important: product_detail must always be the last, otherwise it will overlap other addresses.
    # also product_urlpatterns should also be at the end of urlpatterns
    re_path('^(?P<id>.+)/$', ProductRetrieveView.as_view(), name='product-detail'),
]

urlpatterns = additions_urlpatterns + genres_urlpatterns + reviews_urlpatterns + products_urlpatterns
