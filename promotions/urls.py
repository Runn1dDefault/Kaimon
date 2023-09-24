from django.urls import path, re_path

from .views import PromotionListView, PromotionProductListView


urlpatterns = [
    path('', PromotionListView.as_view(), name='promotions_list'),
    re_path('^products/(?P<id>.+)/$', PromotionProductListView.as_view(), name='promotions_products_list')
]
