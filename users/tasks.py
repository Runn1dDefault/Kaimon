import logging
from copy import deepcopy

from django.conf import settings
from django.core.cache import caches
from django.core.mail import send_mail
from django.template.loader import render_to_string

from kaimon.celery import app
from users.utils import smp_cache_key_for_email


@app.task()
def send_code_template(email: str, code: str | int):
    template_data = deepcopy(settings.RESTORE_VERIFY_TEMPLATE)
    template_data['code'] = code

    html_message = render_to_string('restore_code.html', context=template_data)
    plain_message = settings.VERIFICATION_PLAIN_TEXT.format(**template_data)
    try:
        send_mail(
            subject='Kaimono',
            message=plain_message,
            from_email=None,
            recipient_list=[email],
            html_message=html_message
        )
    except Exception as e:
        logging.error(e)
    else:
        cache = caches['users']
        cache.set(smp_cache_key_for_email(email), code, timeout=300)
