import copy
from typing import Iterable

from django.contrib.auth.password_validation import validate_password
from django.utils.functional import cached_property
from django.utils.translation import gettext_lazy as _
from rest_framework import serializers

from .exceptions import InvalidRestoreCode, RestoreCodeExist
from .models import User
from .tasks import send_code_template
from .tokens import get_tokens_for_user, RestoreToken, RestoreCode


class UserProfileSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ('email', 'full_name', 'role', 'image')
        extra_kwargs = {'role': {'read_only': True}}

    def __init__(self, hide_fields: Iterable[str] = None, instance=None, data=None, **kwargs):
        self.hide_fields = hide_fields or []
        super().__init__(instance=instance, data=data, **kwargs)

    @cached_property
    def fields(self):
        fields = super().fields
        for field in copy.deepcopy(fields).keys():
            if field in self.hide_fields:
                fields.pop(field)
        return fields


class PasswordSerializer(serializers.Serializer):
    password = serializers.CharField(min_length=8, validators=[validate_password], write_only=True, required=True)
    password2 = serializers.CharField(min_length=8, write_only=True, required=True)

    def validate(self, attrs):
        pwd = attrs['password']
        pwd2 = attrs.pop('password2', None)
        if pwd != pwd2:
            raise serializers.ValidationError({'detail': 'passwords not match!'})
        return attrs

    def update(self, instance, validated_data):
        raise NotImplementedError('`update()` must be implemented.')

    def create(self, validated_data):
        raise NotImplementedError('`create()` must be implemented.')


class RegistrationSerializer(PasswordSerializer):
    full_name = serializers.CharField(max_length=300, required=True)
    email = serializers.EmailField(max_length=300, required=True)
    image = serializers.ImageField(required=False, allow_empty_file=False, write_only=True)

    def create(self, validated_data):
        email = validated_data['email']
        return User.objects.create_user(
            username=email,
            email=email,
            password=validated_data['password'],
            full_name=validated_data['full_name'],
            is_active=False,
            registration_payed=False,
            image=validated_data.get('image', None)
        )

    def update(self, instance, validated_data):
        raise NotImplementedError('`update()` not implemented.')

    def to_representation(self, instance):
        raise NotImplementedError('`to_representation()` not implemented.')

    @property
    def data(self):
        assert self.instance
        return UserProfileSerializer(instance=self.instance, many=False, context=self.context).data


class RestoreSerializer(serializers.Serializer):
    RESTORE_TOKEN_CLASS = RestoreToken
    RESTORE_CODE_CLASS = RestoreCode

    email = serializers.EmailField(write_only=True, required=True)
    code = serializers.CharField(write_only=True, required=False, min_length=6, max_length=6)
    send_new_code = serializers.BooleanField(default=False)

    def __init__(self, data, **kwargs):
        super().__init__(data=data, instance=None, **kwargs)

    def create(self, validated_data):
        raise NotImplementedError('`create()` not implemented.')

    def update(self, instance, validated_data):
        raise NotImplementedError('`update()` not implemented.')

    def create_token(self, user_id: int, code):
        try:
            token = self.RESTORE_TOKEN_CLASS.for_user(user_id=user_id, code=code)
        except InvalidRestoreCode as e:
            raise serializers.ValidationError({'detail': _(str(e))})
        else:
            self.RESTORE_CODE_CLASS(sub=user_id).remove()
            return token

    def create_code(self, user_id: int, raise_on_exist: bool):
        try:
            code = self.RESTORE_CODE_CLASS.for_user(user_id=user_id, raise_on_exist=raise_on_exist)
        except RestoreCodeExist as e:
            raise serializers.ValidationError({'code': _(str(e))})
        else:
            return code

    def validate(self, attrs):
        email = attrs.pop('email')
        user = User.objects.filter(email=email).first()
        if not user:
            raise serializers.ValidationError({'email': _('User with email %s not exist!') % email})

        code = attrs.pop('code', None)
        send_new_code = attrs['send_new_code']
        if not code and not send_new_code:
            raise serializers.ValidationError({'code': _('Invalid code!')})

        if code:
            token = self.create_token(user_id=user.id, code=code)
            return {'token': str(token)}

        if send_new_code is True:
            # if you need to restrict sending for a user who has already sent, then change raise_on_exist to True
            new_code = self.create_code(user_id=user.id, raise_on_exist=False)
            send_code_template.delay(email=email, code=str(new_code))
            return {'sent': True}
        raise serializers.ValidationError({'detail': _('Something went wrong!')}, code=500)

    def to_representation(self, validated_data):
        token = validated_data.get('token')
        if token:
            return {'status': 'ok', 'token': token}
        if validated_data.get('sent', False) is True:
            return {'status': 'send'}
        return {'status': 'failed'}


class UpdatePasswordSerializer(PasswordSerializer):
    def create(self, validated_data):
        raise NotImplementedError('`create()` not implemented.')

    def update(self, instance, validated_data):
        instance.set_password(validated_data['password'])
        instance.save()
        return instance

    def to_representation(self, instance):
        return get_tokens_for_user(instance)
