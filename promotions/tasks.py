from django.utils import timezone

from kaimon.celery import app

from .models import Promotion


@app.task()
def deactivate_promotions():
    today = timezone.now().date()
    promotions = Promotion.objects.filter(deactivated=False, end_date__lte=today)
    if promotions.exists():
        promotions.update(deactivated=True)
