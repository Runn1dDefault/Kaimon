from django.contrib.auth.password_validation import validate_password
from django.utils.translation import gettext_lazy as _
from rest_framework import serializers

from .exceptions import InvalidRestoreCode, RestoreCodeExist
from .models import User
from .tasks import send_code_template
from .tokens import get_tokens_for_user, RestoreToken, RestoreCode
from .validators import validate_full_name


class UserProfileSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ('email', 'full_name', 'role', 'image')


class PasswordSerializer(serializers.Serializer):
    password = serializers.CharField(min_length=8, validators=[validate_password], write_only=True, required=True)
    password2 = serializers.CharField(min_length=8, write_only=True, required=True)

    def validate(self, attrs):
        pwd = attrs['password']
        pwd2 = attrs.pop('password2', None)
        if pwd != pwd2:
            raise serializers.ValidationError({'detail': 'passwords not match!'})
        return attrs


class RegistrationSerializer(PasswordSerializer):
    _user_serializer = UserProfileSerializer
    full_name = serializers.CharField(max_length=300, required=True, validators=[validate_full_name])
    email = serializers.EmailField(max_length=300, required=True)

    def _get_user_data(self, user):
        return self._user_serializer(instance=user, context=self.context).data

    def validate(self, attrs):
        attrs = super().validate(attrs)
        email = attrs['email']
        user = User.objects.create_user(
            username=email,
            email=email,
            password=attrs['password'],
            full_name=attrs['full_name'],
            is_active=False,
            registration_payed=False
        )
        return self._get_user_data(user)


class RestoreSerializer(serializers.Serializer):
    RESTORE_TOKEN_CLASS = RestoreToken
    RESTORE_CODE_CLASS = RestoreCode

    email = serializers.EmailField(write_only=True, required=True)
    code = serializers.CharField(write_only=True, required=False, min_length=6, max_length=6)
    send_new_code = serializers.BooleanField(default=False)

    @staticmethod
    def _get_user_by_email(email):
        user = User.objects.filter(email=email).first()
        if not user:
            raise serializers.ValidationError({'detail': _('User with email %s not exist!') % email})
        return user

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
            raise serializers.ValidationError({'detail': _(str(e))})
        else:
            return code

    def validate(self, attrs):
        email = attrs['email']
        user = self._get_user_by_email(email)
        code = attrs.get('code')
        send_new_code = attrs['send_new_code']

        if not code and not send_new_code:
            raise serializers.ValidationError(
                {'detail': _('When send_new_code is false code field become required!')}
            )
        if code:
            token = self.create_token(user_id=user.id, code=code)
            return {'token': str(token)}

        if send_new_code is True:
            # if you need to restrict sending for a user who has already sent, then change raise_on_exist to True
            code = self.create_code(user_id=user.id, raise_on_exist=False)
            send_code_template.delay(email=email, code=str(code))
            return {'status': 'send'}
        return {'status': 'failed'}


class UpdatePasswordSerializer(PasswordSerializer):
    def validate(self, attrs):
        user = self.context['request'].user
        attrs = super().validate(attrs)
        user.set_password(attrs['password'])
        user.save()
        return get_tokens_for_user(user)
