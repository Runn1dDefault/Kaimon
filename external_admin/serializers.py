from typing import Any

from django.core.validators import MaxValueValidator
from django.db import transaction
from django.db.models import F, Case, When, Value
from django.db.models.functions import Round
from rest_framework import serializers

from currencies.models import Conversion
from currencies.serializers import ConversionField
from product.models import Product, Genre, Tag, ProductImageUrl, TagGroup, ProductReview
from product.utils import get_genre_parents_tree
from promotions.models import Banner, Promotion, Discount
from order.models import Order, Customer, DeliveryAddress, OrderReceipt
from users.models import User
from utils.serializers import AnalyticsSerializer


class UserAdminSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ('id', 'email', 'full_name', 'role', 'is_active', 'date_joined', 'last_login', 'registration_payed')
        extra_kwargs = {'role': {'read_only': True}}


class ConversionAdminSerializer(serializers.ModelSerializer):
    class Meta:
        model = Conversion
        fields = ('id', 'currency_from', 'currency_to', 'price_per')
        extra_kwargs = {'currency_from': {'read_only': True}, 'currency_to': {'read_only': True}}


class TagAdminSerializer(serializers.ModelSerializer):
    class Meta:
        model = Tag
        fields = '__all__'


class GenreAdminSerializer(serializers.ModelSerializer):
    class Meta:
        model = Genre
        fields = '__all__'


class ProductImageAdminSerializer(serializers.ModelSerializer):
    product = serializers.PrimaryKeyRelatedField(queryset=Product.objects.all(), write_only=True, required=True)
    url = serializers.URLField(required=True)

    class Meta:
        model = ProductImageUrl
        fields = ('id', 'product', 'url')


class ProductAdminSerializer(serializers.ModelSerializer):
    price = ConversionField(all_conversions=True)
    sale_price = ConversionField(all_conversions=True)
    avg_rank = serializers.SerializerMethodField(read_only=True)
    image_urls = serializers.SlugRelatedField(many=True, read_only=True, slug_field='url')

    class Meta:
        model = Product
        fields = ('id', 'name', 'price', 'sale_price', 'availability', 'avg_rank', 'reviews_count', 'image_urls',
                  'created_at', 'description')


class TagGroupAdminSerializer(serializers.ModelSerializer):
    class Meta:
        model = TagGroup
        fields = '__all__'


class ProductDetailAdminSerializer(ProductAdminSerializer):
    product_url = serializers.URLField(required=False)
    genre = serializers.PrimaryKeyRelatedField(queryset=Genre.objects.exclude(level=0), many=False, write_only=True,
                                               required=True)
    tags = serializers.PrimaryKeyRelatedField(
        queryset=Tag.objects.all(),
        write_only=True,
        required=False,
        many=True
    )
    image_urls = ProductImageAdminSerializer(many=True, read_only=True)
    images = serializers.ListField(child=serializers.URLField(), write_only=True, required=False)
    tags_info = serializers.SerializerMethodField(read_only=True)

    class Meta:
        model = Product
        fields = (
            *ProductAdminSerializer.Meta.fields, 'name_ru', 'name_en', 'name_tr', 'name_ky', 'name_kz',
            'description_ru', 'description_en', 'description_tr', 'description_ky', 'description_kz',
            'is_active', 'tags_info', 'reference_rank', 'genre', 'tags', 'images', 'product_url'
        )
        extra_kwargs = {'id': {'read_only': True}, 'price': {'required': True}}

    def get_tags_info(self, instance):
        if not instance.tags.exists():
            return []
        group_ids = list(instance.tags.all().order_by('group_id')
                                            .distinct('group_id')
                                            .values_list('group_id', flat=True))

    def get_tags_info(self, instance):
        tags_fk = instance.tags.all()
        if not tags_fk.exists():
            return []

        group_ids = tags_fk.order_by('tag__group_id').distinct('tag__group_id').values_list('tag__group_id',
                                                                                            flat=True)
        groups_queryset = TagGroup.objects.filter(id__in=group_ids)
        tag_translate_field = self.get_translate_field('name')
        return groups_queryset.tags_list(
            name_field=tag_translate_field,
            tag_ids=tags_fk.values_list('tag_id', flat=True)
        )

    def create(self, validated_data):
        images = validated_data.pop('images', None)
        genre = validated_data.pop('genre')
        tags = validated_data.pop('tags', None)
        genres_tree = get_genre_parents_tree(genre)

        with transaction.atomic():
            product = super().create(validated_data)
            product.genres.add(*genres_tree)
            if images:
                ProductImageUrl.objects.bulk_create([ProductImageUrl(product=product, url=url) for url in images])
            if tags:
                product.tags.add(*tags)
            product.save()
        return product

    def update(self, instance, validated_data):
        genre = validated_data.pop('genre', None)
        tags = validated_data.pop('tags', None)
        product = super().update(instance, validated_data)
        save = False
        if genre:
            genres_tree = get_genre_parents_tree(genre)
            product.genres.clear()
            product.genres.add(*genres_tree)
            save = True
        if tags:
            product.tags.clear()
            product.tags.add(*tags)
            save = True
        if save:
            product.save()
        return product


class ProductReviewAdminSerializer(serializers.ModelSerializer):
    user = UserAdminSerializer(read_only=True)
    product = ProductAdminSerializer(many=False, read_only=True)
    product_id = serializers.PrimaryKeyRelatedField(queryset=Product.objects.all(), write_only=True, required=True)

    class Meta:
        model = ProductReview
        fields = ('id', 'user', 'product', 'product_id', 'rank', 'is_read', 'is_active', 'comment', 'created_at')


class BannerAdminSerializer(serializers.ModelSerializer):
    class Meta:
        model = Banner
        fields = '__all__'


class PromotionAdminSerializer(serializers.ModelSerializer):
    name = serializers.CharField(write_only=True, required=True)
    name_ru = serializers.CharField(write_only=True, required=False)
    name_en = serializers.CharField(write_only=True, required=False)
    name_tr = serializers.CharField(write_only=True, required=False)
    name_kz = serializers.CharField(write_only=True, required=False)
    name_ky = serializers.CharField(write_only=True, required=False)
    description = serializers.CharField(write_only=True, required=False)
    description_ru = serializers.CharField(write_only=True, required=False)
    description_en = serializers.CharField(write_only=True, required=False)
    description_tr = serializers.CharField(write_only=True, required=False)
    description_kz = serializers.CharField(write_only=True, required=False)
    description_ky = serializers.CharField(write_only=True, required=False)
    image = serializers.ImageField(write_only=True, required=False)

    set_products = serializers.PrimaryKeyRelatedField(queryset=Product.objects.all(), write_only=True, many=True,
                                                      required=False)
    set_discount = serializers.FloatField(validators=[MaxValueValidator(100)], write_only=True, required=False)

    discount = serializers.SlugRelatedField(slug_field='percentage', read_only=True)
    banner = BannerAdminSerializer(many=False, read_only=True)
    products = ProductAdminSerializer(many=True, read_only=True)

    class Meta:
        model = Promotion
        banner_fields = ('name', 'name_ru', 'name_en', 'name_tr', 'name_ky', 'name_kz', 'description',
                         'description_ru', 'description_en', 'description_tr', 'description_ky', 'description_kz',
                         'image')
        fields = ('id', 'discount', 'set_discount', 'banner', 'products', 'set_products', 'start_date', 'end_date',
                  'deactivated', 'created_at', *banner_fields)

    def collect_banner_data(self, validated_data) -> dict[str, Any]:
        banner_data = {}
        fields = list(validated_data.keys())
        for field in fields:
            if field in self.Meta.banner_fields:
                banner_data[field] = validated_data.pop(field)
        return banner_data

    def create(self, validated_data):
        discount = validated_data.pop('set_discount', None)
        products = validated_data.pop('set_products', None)
        banner_data = self.collect_banner_data(validated_data)

        with transaction.atomic():
            banner_serializer = BannerAdminSerializer(data=banner_data, many=False, context=self.context)
            banner_serializer.is_valid(raise_exception=True)
            banner_serializer.save()
            validated_data['banner_id'] = banner_serializer.instance.id
            promotion = super().create(validated_data)
            if discount:
                Discount.objects.create(promotion=promotion, percentage=discount)
            if products:
                promotion.products.add(*products)
                promotion.save()
        return promotion

    def update(self, instance, validated_data):
        discount = validated_data.pop('set_discount', None)
        if discount:
            instance.discount.percentage = discount
            instance.discount.save()
        product_ids = validated_data.pop('product_ids', None)
        if product_ids:
            instance.products.clear()
            instance.products.add(*product_ids)
        banner_data = self.collect_banner_data(validated_data)
        banner_serializer = BannerAdminSerializer(
            instance=instance.banner,
            data=banner_data,
            partial=self.partial,
            many=False,
            context=self.context
        )
        banner_serializer.is_valid(raise_exception=True)
        banner_serializer.save()
        return super().update(instance, validated_data)


class OrderCustomerAdminSerializer(serializers.ModelSerializer):
    class Meta:
        model = Customer
        fields = ('id', 'name', 'email', 'phone')


class DeliveryAddressAdminSerializer(serializers.ModelSerializer):
    user = UserAdminSerializer(read_only=True)

    class Meta:
        model = DeliveryAddress
        fields = '__all__'


class OrderReceiptAdminSerializer(serializers.ModelSerializer):
    class Meta:
        model = OrderReceipt
        fields = '__all__'


class OrderAdminSerializer(serializers.ModelSerializer):
    customer = OrderCustomerAdminSerializer(read_only=True)
    delivery_address = DeliveryAddressAdminSerializer(read_only=True)
    receipts = OrderReceiptAdminSerializer(many=True, read_only=True)
    total_price = serializers.SerializerMethodField(read_only=True)

    class Meta:
        model = Order
        fields = ('id', 'customer', 'delivery_address', 'status', 'receipts', 'total_price')

    def get_total_price(self, instance):
        receipts = instance.receipts.filter(quantity__gt=0, unit_price__gt=0)
        sale_formula = F('unit_price') - (F('discount') * F('unit_price') / Value(100.0))
        return sum(
            receipts.annotate(
                total_price=Case(
                    When(
                        discount=0,
                        then=Round(
                            F('unit_price') * F('quantity'),
                            precision=2
                        )
                    ),
                    When(
                        discount__gt=0,
                        then=Round(sale_formula * F('quantity'), precision=2)
                    )
                )
            ).values_list('total_price', flat=True)
        )


# ------------------------------------------------- Analytics ----------------------------------------------------------
class OrderAnalyticsSerializer(AnalyticsSerializer):
    class Meta:
        model = Order
        hide_fields = ('sale_prices_yen', 'sale_prices_som', 'sale_prices_dollar')
        empty_data_template = {"receipts_info": [], "yen": 0, "som": 0, "dollar": 0}

    def filtered_analytics(self, start, end, filter_by):
        model = getattr(self.Meta, 'model')
        base_queryset = model.analytics.filter(created_at__date__gte=start, created_at__date__lte=end)
        return base_queryset.get_analytics(filter_by)

    def to_representation(self, df):
        if df.empty is False:
            df['yen'] = df['sale_prices_yen'].apply(lambda x: sum(x))
            df['som'] = df['sale_prices_som'].apply(lambda x: sum(x))
            df['dollar'] = df['sale_prices_dollar'].apply(lambda x: sum(x))
        return super().to_representation(df)


class UserAnalyticsSerializer(AnalyticsSerializer):
    class Meta:
        model = User
        empty_data_template = {"users": [], "count": 0}

    def filtered_analytics(self, start, end, filter_by):
        model = getattr(self.Meta, 'model')
        base_queryset = model.analytics.filter(date_joined__date__gte=start, date_joined__date__lte=end)
        return base_queryset.get_joined_users_analytics(filter_by)

    def users_representation(self, users):
        request = self.context['request']
        for user in users:
            image = user.get('image')
            if image:
                user['image'] = request.build_absolute_uri(image)
        return users

    def to_representation(self, df):
        if df.empty is False:
            df['users'] = df['users'].apply(lambda x: self.users_representation(x))
        return super().to_representation(df)


class ReviewAnalyticsSerializer(AnalyticsSerializer):
    class Meta:
        model = ProductReview
        empty_data_template = {'info': [], 'count': 0, 'avg_rank': 0.0}

    def filtered_analytics(self, start, end, filter_by):
        model = getattr(self.Meta, 'model')
        base_queryset = model.analytics.filter(created_at__date__gte=start, created_at__date__lte=end)
        return base_queryset.get_date_analytics(filter_by)
