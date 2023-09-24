from typing import Iterable

from django.conf import settings
from django.contrib.auth.password_validation import validate_password
from django.utils.translation import gettext_lazy as _
from rest_framework import serializers

from .models import User
from .tasks import send_code_template
from .tokens import get_tokens_for_user, generate_restore_token, generate_confirm_code


class RestoreSerializer(serializers.Serializer):
    email = serializers.EmailField(write_only=True, required=True)
    code = serializers.CharField(write_only=True, required=False, min_length=6, max_length=6)
    send_new_code = serializers.BooleanField(default=False)

    def __init__(self, data, **kwargs):
        super().__init__(data=data, instance=None, **kwargs)

    def create(self, validated_data):
        raise NotImplementedError('`create()` not implemented.')

    def update(self, instance, validated_data):
        raise NotImplementedError('`update()` not implemented.')

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
            token = generate_restore_token(user_id=user.id, code=code)
            return {'token': str(token)}

        if send_new_code is True:
            # if you need to restrict sending for a user who has already sent, then change raise_on_exist to True
            new_code = generate_confirm_code(user_id=user.id, raise_on_exist=False)
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


class UserProfileSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ('email', 'full_name', 'role', 'image')
        extra_kwargs = {'role': {'read_only': True}}

    def __init__(self, hide_fields: Iterable[str] = None, instance=None, data=None, **kwargs):
        self.hide_fields = hide_fields or []
        super().__init__(instance=instance, data=data, **kwargs)

    @property
    def _readable_fields(self):
        for field_name, field_ins in self.fields.items():
            # this will prevent a representation field from appearing
            if field_name in self.hide_fields:
                continue

            if not field_ins.write_only:
                yield field_ins


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
        user = User.objects.create_user(
            username=email,
            email=email,
            password=validated_data['password'],
            full_name=validated_data['full_name'],
            registration_payed=False,
            email_confirmed=False,
            image=validated_data.get('image', None)
        )
        # send email confirmation code
        new_code = generate_confirm_code(
            user_id=user.id,
            raise_on_exist=False,
            live_seconds=settings.EMAIL_CONFIRM_CODE_LIVE
        )
        send_code_template.delay(email=email, code=str(new_code))
        return user

    def update(self, instance, validated_data):
        raise NotImplementedError('`update()` not implemented.')

    def to_representation(self, instance):
        return get_tokens_for_user(instance)


class ConfirmEmailSerializer(serializers.Serializer):
    code = serializers.CharField(write_only=True, required=True, max_length=6, min_length=6)

    def validate(self, attrs):
        code = attrs['code']
        generate_restore_token(user_id=self.instance.id, code=code)
        return attrs

    def update(self, instance, validated_data):
        instance.email_confirmed = True
        instance.save()
        return instance

    def create(self, validated_data):
        raise NotImplementedError('`create()` not implemented.')

    def to_representation(self, instance):
        return get_tokens_for_user(instance)


class UpdatePasswordSerializer(PasswordSerializer):
    def create(self, validated_data):
        raise NotImplementedError('`create()` not implemented.')

    def update(self, instance, validated_data):
        instance.set_password(validated_data['password'])
        instance.save()
        return instance

    def to_representation(self, instance):
        return get_tokens_for_user(instance)
