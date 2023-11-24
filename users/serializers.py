from typing import Iterable

from django.conf import settings
from django.contrib.auth.password_validation import validate_password
from django.core.cache import caches
from django.utils.text import slugify
from django.utils.translation import gettext_lazy as _
from rest_framework import serializers
from rest_framework.fields import empty

from .models import User
from .tasks import send_code_template
from .tokens import get_tokens_for_user, generate_restore_token, generate_confirm_code
from .utils import smp_cache_key_for_email


class UserProfileSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ('email', 'full_name', 'role', 'image', 'email_confirmed', 'registration_payed')
        extra_kwargs = {
            'role': {'read_only': True},
            'email_confirmed': {'read_only': True},
            'registration_payed': {'read_only': True},
        }

    def __init__(self, instance=None, data=empty, show_fields: Iterable[str] = None, **kwargs):
        self.show_fields = show_fields or []
        super().__init__(instance=instance, data=data, **kwargs)

    def validate(self, attrs):
        email = attrs.get('email')
        if email and User.objects.filter(email=email).exists():
            raise serializers.ValidationError({'email': _('Already exists!')})
        return attrs
    
    def update(self, instance, validated_data):
        email = validated_data.get('email')
        if email and (email != instance.email or instance.email_confirmed is False):
            new_code = generate_confirm_code(
                user_id=instance.id,
                raise_on_exist=True,
                live_seconds=settings.EMAIL_CONFIRM_CODE_LIVE
            )
            send_code_template.delay(email=email, code=str(new_code))
            validated_data['email_confirmed'] = False
            validated_data['username'] = slugify(email)
        return super().update(instance, validated_data)

    @property
    def _readable_fields(self):
        for field_name, field_ins in self.fields.items():
            # this will prevent a representation field from appearing
            if self.show_fields and field_name not in self.show_fields:
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
        if User.objects.filter(email=email).exists():
            raise serializers.ValidationError({'email': 'Already exists!'})

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


class BaseRecoverySerializer(serializers.Serializer):
    email = serializers.EmailField(write_only=True, required=True)

    def __init__(self, data=None, **kwargs):  # data!=empty for raising error on None
        super().__init__(data=data, instance=None, **kwargs)
        self._user = None

    def validate_email(self, email):
        self._user = User.objects.filter(email=email).first()
        if not self._user:
            raise serializers.ValidationError({'email': _('User with email %s not exist!') % email})
        return email

    def create(self, validated_data):
        raise NotImplementedError('`create()` not implemented!')

    def update(self, instance, validated_data):
        raise NotImplementedError('`update()` not implemented!')

    def to_representation(self, validated_data):
        return validated_data


class RecoveryCodeSerializer(BaseRecoverySerializer):
    def validate(self, attrs):
        email = self._user.email
        cache = caches['users']
        cache_key = smp_cache_key_for_email(email)
        if cache.get(cache_key):
            raise serializers.ValidationError(
                {"email": _("Can't send message to %s for another %s seconds" % (email, cache.ttl(cache_key)))}
            )

        # if you need to restrict sending for a user who has already sent, then change raise_on_exist to True
        new_code = generate_confirm_code(user_id=self._user.id, raise_on_exist=False)
        send_code_template(email=email, code=str(new_code))
        return {'status': 'send'}


class RecoveryTokenSerializer(BaseRecoverySerializer):
    code = serializers.CharField(write_only=True, required=True, min_length=6, max_length=6)

    def validate(self, attrs):
        token = generate_restore_token(user_id=self._user.id, code=attrs['code'])
        return {'status': 'ok', 'token': str(token)}


class UpdatePasswordSerializer(PasswordSerializer):
    def create(self, validated_data):
        raise NotImplementedError('`create()` not implemented.')

    def update(self, instance, validated_data):
        instance.set_password(validated_data['password'])
        instance.save()
        return instance

    def to_representation(self, instance):
        return get_tokens_for_user(instance)
