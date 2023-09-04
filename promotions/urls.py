from django.urls import path, re_path

from .views import PromotionListView, PromotionRetrieveView


urlpatterns = [
    path('', PromotionListView.as_view(), name='promotions_list'),
    re_path('^(?P<id>.+)/$', PromotionRetrieveView.as_view(), name='promotions_retrieve')
]
