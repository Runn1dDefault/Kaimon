from django.urls import path

from .views import UserListView, UserSearchView, block_or_unblock_user_view

urlpatterns = [
    path('users/', UserListView.as_view(), name='admin_users_list'),
    path('users/search/', UserSearchView.as_view(), name='admin_users_search'),
    path('users/block-or-unblock/', block_or_unblock_user_view, name='admin_users_blocking'),
]
