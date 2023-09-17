import logging
from copy import deepcopy

from django.conf import settings
from django.core.cache import caches
from django.core.mail import send_mail
from django.template.loader import render_to_string

from kaimon.celery import app


@app.task()
def send_code_template(email: str, code: str | int):
    cache = caches['users']
    cache_key = 'smtp:' + email
    if cache.get(cache_key):
        logging.error("Can't send message to email %s for another %s seconds" % (email, cache.ttl(cache_key)))
        return

    template_data = deepcopy(settings.RESTORE_VERIFY_TEMPLATE)
    template_data['code'] = code

    html_message = render_to_string('restore_code.html', context=template_data)
    plain_message = ''  # TODO: add plain text

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
        cache.set(cache_key, code, timeout=300)
