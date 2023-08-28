from django.urls import path, re_path

from .views import AdminUpdateConversionView, AdminConversionListView


urlpatterns = [
    re_path('^conversion/(?P<id>.+)/$', AdminUpdateConversionView.as_view(), name='admin_conversion_update'),
    path('conversion/', AdminConversionListView.as_view(), name='admin_conversion_list')
]
