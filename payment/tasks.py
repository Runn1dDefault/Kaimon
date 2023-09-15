from django.contrib.auth import get_user_model

from kaimon.celery import app


@app.task()
def registration_payed_for_user(user_id):
    user = get_user_model().objects.get(id=user_id)
    user.registration_payed = True
    user.is_active = True
    user.save()

