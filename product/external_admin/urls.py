from django.urls import path, include
from rest_framework.routers import SimpleRouter

from .views import AdminProductListView, AdminReviewView, get_new_reviews_count


router = SimpleRouter()
router.register('reviews', AdminReviewView)

urlpatterns = [
    path('products/', AdminProductListView.as_view(), name='admin_product_list'),
    path('new-reviews/count/', get_new_reviews_count, name='admin_reviews'),
    path('', include(router.urls)),
]
