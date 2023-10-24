from django.utils import timezone

from kaimon.celery import app

from .models import Promotion


@app.task()
def deactivate_promotions():
    promotions = Promotion.objects.filter(end_date=timezone.now().date())

    if promotions.exists():
        promotions.update(deactivated=True)


@app.task()
def activate_promotions():
    promotions = Promotion.objects.filter(start_date=timezone.now().date())

    if promotions.exists():
        promotions.update(deactivated=False)
