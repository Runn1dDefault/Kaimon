from django.urls import path

from .views import ConversionListView

urlpatterns = [
    path('', ConversionListView.as_view(), name='conversions-list'),
]
