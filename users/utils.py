from django.contrib.auth import get_user_model


def get_sentinel_user():
    user, _ = get_user_model().objects.get_or_create(username="deleted")
    if user.is_active is True:
        user.is_active = False
        user.save()
    return user
