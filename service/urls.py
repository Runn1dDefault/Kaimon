from django.urls import path

from .views import ConversionListView


urlpatterns = [
    path('conversions/', ConversionListView.as_view(), name='conversions-list'),
]
