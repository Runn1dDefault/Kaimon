from django.conf import settings
from django.core.mail import send_mail

from kaimono.celery import app
from users.models import User
from users.tokens import RestoreCode


@app.task()
def send_code(email: str):
    user = User.objects.get(email=email)
    # if you need to restrict sending for a user who has already sent, then change raise_exist to True
    code = RestoreCode.for_user(user=user, raise_exist=False)
    print(code)
    send_mail(
        subject="Password restore code",
        message="Code: %s" % code,
        from_email=settings.MAILING_FROM_EMAIL,
        recipient_list=[email],
        fail_silently=False
    )
