from django.urls import path, re_path, include
from rest_framework.routers import SimpleRouter

from .views import get_languages_view, GenreProductsListView, SearchProductView, GenreReadViewSet, NewProductsView, \
    ProductReviewView

router = SimpleRouter()
router.register('', GenreReadViewSet, basename='product_genres')


urlpatterns = [
    path('languages/', get_languages_view, name='product_languages_list'),
    path('genres/', include(router.urls)),
    re_path('^genres/(?P<id>.+)/products/$', GenreProductsListView.as_view(), name='product_genre_products'),
    path('search/', SearchProductView.as_view(), name='product_search'),
    path('new/', NewProductsView.as_view(), name='product_new'),
    re_path('^product/(?P<id>.+)/reviews/', ProductReviewView.as_view(), name='product_review')

]
