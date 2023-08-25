from rest_framework import serializers

from product.mixins import LangSerializerMixin
from product.models import Genre, Product, Marker, ProductDetail


class GenreSerializer(serializers.ModelSerializer, LangSerializerMixin):
    class Meta:
        model = Genre
        fields = ('id', 'name', 'level')
        translate_fields = ('name',)


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
    genres = GenreSerializer(many=True)
    marker = MarkerSerializer(many=False)
    details = ProductDetailSerializer(many=True)

    class Meta:
        model = Product
        fields = ('id', 'name', 'price', 'image_url', 'description', 'brand_name', 'marker', 'genres', 'details')
        translate_fields = ('name', 'description', 'brand_name',)
