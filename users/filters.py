from rest_framework.filters import BaseFilterBackend


class FilterByUser(BaseFilterBackend):
    def _get_user_relation_field(self, view, request):
        field = getattr(view, 'user_relation_field', None)
        if not field:
            raise AttributeError('user_relation_field attribute is required!')
        return getattr(request.user, field, None)

    def _get_filters(self, view):
        return getattr(view, 'user_relation_filters', {})

    def filter_queryset(self, request, queryset, view):
        user_relation_field = self._get_user_relation_field(view, request)
        assert user_relation_field
        return user_relation_field.filter(**self._get_filters(view))

