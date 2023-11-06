from collections import OrderedDict
from decimal import Decimal

from django.core.exceptions import ValidationError
from django.utils.encoding import force_str
from django.utils.translation import gettext_lazy as _
from rest_framework import serializers
from rest_framework.filters import BaseFilterBackend
from rest_framework.compat import coreapi, coreschema


class ListFilterFields(BaseFilterBackend):
    description = _('Filtering by field %s ex: query1,query2')
    filter_fields_arr = 'list_filter_fields'

    def get_field_names(self, view):
        return getattr(view, self.filter_fields_arr, {})

    def get_queries_kwargs(self, request, view) -> dict[str, list[str]]:
        queries = {}
        for field_name, source in self.get_field_names(view).items():
            params = [i for i in request.query_params.get(field_name, '').split(',') if i.strip()]
            if params:
                queries[source + '__in'] = params
        return queries

    def filter_queryset(self, request, queryset, view):
        queries = self.get_queries_kwargs(request, view)
        if queries:
            return queryset.filter(**queries)
        return queryset

    def get_schema_operation_parameters(self, view):
        return [
            {
                'name': field_name,
                'required': False,
                'in': 'query',
                'description': force_str(self.description % source),
                'schema': {
                    'type': 'string',
                },
            }
            for field_name, source in self.get_field_names(view).items()
        ]


class DateRangeFilter(BaseFilterBackend):
    start_field_attr = 'start_field'
    start_param_attr = 'start_param'
    description = _('Filter by date')

    end_field_attr = 'end_field'
    end_param_attr = 'end_param'

    def get_start_field(self, view):
        return getattr(view, self.start_field_attr)

    def get_start_param_attribute(self, view):
        return getattr(view, self.start_param_attr)

    def get_start_param(self, request, view):
        attr_name = self.get_start_param_attribute(view)
        return request.query_params.get(attr_name)

    def get_end_field(self, view):
        return getattr(view, self.end_field_attr)

    def get_end_param_attribute(self, view):
        return getattr(view, self.end_param_attr)

    def get_end_param(self, request, view):
        attr_name = self.get_end_param_attribute(view)
        return request.query_params.get(attr_name)

    def filter_queryset(self, request, queryset, view):
        start = self.get_start_param(request, view)
        end = self.get_end_param(request, view)

        if not start and not end:
            return queryset

        range_queries = {}
        if start:
            range_queries[self.get_start_field(view) + '__gte'] = start
        if end:
            range_queries[self.get_end_field(view) + '__lte'] = end
        try:
            return queryset.filter(**range_queries)
        except ValidationError as e:
            raise serializers.ValidationError(str(e))

    def get_schema_operation_parameters(self, view):
        description = force_str(self.description)
        return [
            {
                'name': self.get_start_param_attribute(view),
                'required': False,
                'in': 'query',
                'description': description,
                'schema': {
                    'type': 'date',
                },
            },
            {
                'name': self.get_end_param_attribute(view),
                'required': False,
                'in': 'query',
                'description': description,
                'schema': {
                    'type': 'date',
                },
            },
        ]


class FilterByFields(BaseFilterBackend):
    description_form = _('Filter by field: {field}')
    filter_fields_arg = 'filter_fields'

    def get_filter_fields(self, view):
        return getattr(view, self.filter_fields_arg, None)

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
                if db_field.get('type') == 'boolean':
                    value = True if value == 'true' else False
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
