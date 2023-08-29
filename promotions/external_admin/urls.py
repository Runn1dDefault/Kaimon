from django.urls import path, re_path

from .views import (
    PromotionAdminListView,
    PromotionAdminRetrieveView,
    PromotionCreateAdminView,
    PromotionDeleteAdminView
)


urlpatterns = [
    path('promotions/', PromotionAdminListView.as_view(), name='admin_promotions_list'),
    path('promotions/create/', PromotionCreateAdminView.as_view(), name='admin_promotions_create'),
    re_path('^promotions/retrieve/(?P<id>.+)/$', PromotionAdminRetrieveView.as_view(), name='admin_promotions_retrieve'),
    re_path('^promotions/delete/(?P<id>.+)/$', PromotionDeleteAdminView.as_view(), name='admin_promotions_delete'),
]
