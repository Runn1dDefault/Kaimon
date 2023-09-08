from collections import OrderedDict
from decimal import Decimal

from django.utils.encoding import force_str
from django.utils.translation import gettext_lazy as _

from rest_framework.filters import BaseFilterBackend
from rest_framework.compat import coreapi, coreschema


class FilterByLookup(BaseFilterBackend):
    def filter_queryset(self, request, queryset, view):
        lookup_url_kwarg = view.lookup_url_kwarg or view.lookup_field

        assert lookup_url_kwarg in view.kwargs, (
            'Expected view %s to be called with a URL keyword argument '
            'named "%s". Fix your URL conf, or set the `.lookup_field` '
            'attribute on the view correctly.' %
            (view.__class__.__name__, lookup_url_kwarg)
        )

        filter_kwargs = {view.lookup_field: view.kwargs[lookup_url_kwarg]}
        return queryset.filter(**filter_kwargs)


class FilterByFields(BaseFilterBackend):
    description_form = _('Filter by field: {field}')

    def get_filter_fields(self, view):
        return getattr(view, 'filter_fields', None)

    def filter_queryset(self, request, queryset, view):
        filter_fields = self.get_filter_fields(view)
        if not filter_fields:
            return queryset

        filter_kwargs = {}
        assert isinstance(filter_fields, dict)

        filtered_queryset = queryset

        for query_field, db_field in filter_fields.items():
            value = request.query_params.get(query_field, None)
            if not value:
                continue

            if isinstance(db_field, str):
                filter_kwargs[db_field] = value
            elif isinstance(db_field, dict):
                filter_kwargs[db_field['db_field']] = value

        return filtered_queryset.filter(**filter_kwargs)

    def get_schema_fields(self, view):
        assert coreapi is not None, 'coreapi must be installed to use `get_schema_fields()`'
        assert coreschema is not None, 'coreschema must be installed to use `get_schema_fields()`'
        filter_fields = self.get_filter_fields(view) or {}
        schema_fields = []
        for query_field, db_field in filter_fields.items():
            field_type = coreschema.String
            field_type_kwargs = dict(
                title=force_str(query_field),
                description=force_str(self.description_form.format(field=query_field))
            )
            if isinstance(db_field, dict):
                match db_field.get('type').lower():
                    case 'boolean':
                        field_type = coreschema.Boolean
                    case 'integer':
                        field_type = coreschema.Integer
                    case 'enum':
                        field_type = coreschema.Enum
                        assert db_field.get('choices')
                        field_type_kwargs['enum'] = list(db_field['choices'])

            schema_fields.append(
                coreapi.Field(
                    name=query_field,
                    required=False,
                    location='query',
                    schema=field_type(**field_type_kwargs)
                )
            )

        return coreschema

    def get_schema_operation_parameters(self, view):
        filter_fields = self.get_filter_fields(view) or {}
        schema_fields_meta = []
        for query_field, db_field in filter_fields.items():
            field_type = 'string'
            additions_type_kwargs = {}

            if isinstance(db_field, dict):
                field_type = db_field.get('type', 'string')
                if field_type == 'enum':
                    choices = [choice for choice, _ in OrderedDict.fromkeys(db_field['choices'])]
                    if all(isinstance(choice, bool) for choice in choices):
                        field_type = 'boolean'
                    elif all(isinstance(choice, int) for choice in choices):
                        field_type = 'integer'
                    elif all(isinstance(choice, (int, float, Decimal)) for choice in choices):
                        field_type = 'number'
                    elif all(isinstance(choice, str) for choice in choices):
                        field_type = 'string'

                    additions_type_kwargs['enum'] = choices

            schema_fields_meta.append(
                {
                    'name': query_field,
                    'required': False,
                    'in': 'query',
                    'description': force_str(self.description_form.format(field=query_field)),
                    'schema': {
                        'type': field_type,
                        **additions_type_kwargs
                    },
                }
            )

        return schema_fields_meta
