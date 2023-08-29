from django.urls import path, re_path, include

from .views import PromotionListView, PromotionRetrieveView


urlpatterns = [
    path('promotions/', PromotionListView.as_view(), name='promotions_list'),
    re_path('^promotions/(?P<id>.+)/$', PromotionRetrieveView.as_view(), name='promotions_retrieve'),
    path('admin/', include('promotions.external_admin.urls'))
]
