from rest_framework import serializers

from users.models import User


class AdminUserSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ('email', 'full_name', 'role', 'is_active', 'date_joined')
        extra_kwargs = {'role': {'read_only': True}}
