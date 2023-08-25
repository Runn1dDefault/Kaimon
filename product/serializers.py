from django.db.models import Q
from rest_framework import serializers

from product.mixins import LangSerializerMixin
from product.models import Genre, Product, Marker, ProductDetail, GenreChild


class GenreChildSerializer(serializers.ModelSerializer, LangSerializerMixin):
    id = serializers.SerializerMethodField(read_only=True)
    name = serializers.SerializerMethodField(read_only=True)
    level = serializers.SerializerMethodField(read_only=True)

    class Meta:
        model = GenreChild
        fields = ('id', 'name', 'level')
        translate_fields = ('name',)

    def __init__(self, for_children: bool = False, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.for_children = for_children

    def get_fk_field(self, instance):
        if self.for_children:
            return instance.child
        return instance.parent

    def valid_translate_instance(self, instance):
        return self.get_fk_field(instance)

    def get_id(self, instance):
        return self.get_fk_field(instance).id

    def get_name(self, instance):
        return self.get_fk_field(instance).name

    def get_level(self, instance):
        return self.get_fk_field(instance).level


class GenreSerializer(serializers.ModelSerializer, LangSerializerMixin):
    children = serializers.SerializerMethodField(read_only=True)

    class Meta:
        model = Genre
        fields = ('id', 'name', 'level', 'children')
        translate_fields = ('name',)

    def get_children(self, instance):
        children = instance.children.filter(
            Q(child__deactivated__isnull=True) | Q(child__deactivated=False)
        ).filter(child__level=instance.level + 1)
        return GenreChildSerializer(instance=children, many=True, for_children=True).data


class MarkerSerializer(serializers.ModelSerializer, LangSerializerMixin):
    class Meta:
        model = Marker
        fields = ('name',)
        translate_fields = ('name',)


class ProductDetailSerializer(serializers.ModelSerializer, LangSerializerMixin):
    class Meta:
        model = ProductDetail
        fields = ('id', 'name', 'value')
        translate_fields = ('name', 'value')


class ProductSerializer(serializers.ModelSerializer, LangSerializerMixin):
    marker = MarkerSerializer(many=False)
    details = ProductDetailSerializer(many=True)

    class Meta:
        model = Product
        fields = ('id', 'name', 'price', 'image_url', 'description', 'brand_name', 'marker', 'details')
        translate_fields = ('name', 'description', 'brand_name',)
