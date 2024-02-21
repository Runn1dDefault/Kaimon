import logging
from copy import deepcopy

from django.conf import settings
from django.core.cache import caches
from django.core.mail import send_mail
from django.template.loader import render_to_string

from kaimon.celery import app
from users.utils import smp_cache_key_for_email


@app.task()
def send_mail_template(email: str, subject: str, content: str | int, warning_text: str):
    template_data = deepcopy(settings.MAILING_TEMPLATE)
    template_data["subject"] = subject
    template_data['content'] = content
    template_data['warning_text'] = warning_text

    html_message = render_to_string('mailing.html', context=template_data)
    plain_message = settings.MAILING_PLAIN_TEXT.format(**template_data)
    send_mail(
        subject=subject,
        message=plain_message,
        from_email=None,
        recipient_list=[email],
        html_message=html_message
    )


@app.task()
def send_code_template(email: str, code: str):
    try:
        send_mail_template(
            email=email,
            subject="Verify your email",
            content=code,
            warning_text="if it wasn't you. Please ignore this message and do not share the code with anyone."
        )
    except Exception as e:
        logging.error(e)
    else:
        cache = caches['users']
        cache.set(smp_cache_key_for_email(email), code, timeout=300)


@app.task()
def send_notification_template(email: str, msg: str, warn_text: str = None):
    send_mail_template(
        email=email,
        subject="Notification",
        content=msg,
        warning_text=warn_text or "if it was not you please contact us."
    )
