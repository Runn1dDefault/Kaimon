from django.urls import path, re_path

from .views import PromotionListView, PromotionProductListView, DiscountProductListView


urlpatterns = [
    path('', PromotionListView.as_view(), name='promotions_list'),
    path('discount-products/', DiscountProductListView.as_view(), name='promotions_products_discount_list'),
    re_path('^(?P<promotion_id>.+)/products/$', PromotionProductListView.as_view(), name='promotions_products_list')
]
