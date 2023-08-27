from django.urls import path, re_path

from .views import UserListView, UserSearchView, block_or_unblock_user_view

urlpatterns = [
    path('users/', UserListView.as_view(), name='admin_users_list'),
    path('users/search/', UserSearchView.as_view(), name='admin_users_search'),
    re_path('^users/block-or-unblock/(?P<user_id>.+)/', block_or_unblock_user_view, name='admin_users_blocking')
]
