from copy import deepcopy

from django.conf import settings
from sendgrid import sendgrid

from kaimon.celery import app


@app.task()
def send_code_template(email: str, code: str | int):
    template_data = deepcopy(settings.RESTORE_VERIFY_TEMPLATE)
    template_data['code'] = code

    sg = sendgrid.SendGridAPIClient(api_key=settings.SENDGRID_API_KEY)
    data = {
        "template_id": settings.RESTORE_VERIFY_CODE_TEMPLATE_ID,
        "personalizations": [{"to": [{"email": email}], "dynamic_template_data": template_data}],
        "from": {"email": settings.MAILING_FROM_EMAIL}
    }
    try:
        # TODO: remove sendgrid and use custom SMTP
        sg.client.mail.send.post(request_body=data)
    except Exception as e:
        print(e)
