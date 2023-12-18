import os.path
from datetime import timedelta

from django.conf import settings
from django.core.exceptions import ObjectDoesNotExist
from django.utils.timezone import now

from kaimon.celery import app
from orders.models import Order, OrderConversion, OrderShipping
from orders.utils import generate_shipping_code, is_success_transaction
from service.models import Currencies
from service.utils import get_currencies_price_per, generate_qrcode


@app.task()
def create_order_conversions(order_id: str):
    order = Order.objects.get(id=order_id)
    new_conversions = []

    for conversion_from in Currencies:
        for conversion_to in Currencies:
            if conversion_from == conversion_to:
                continue

            price_per = get_currencies_price_per(conversion_from, conversion_to)
            if not price_per:
                continue

            new_conversions.append(
                OrderConversion(
                    order=order,
                    currency_from=conversion_from,
                    currency_to=conversion_to,
                    price_per=price_per
                )
            )

    if new_conversions:
        OrderConversion.objects.bulk_create(new_conversions)


@app.task()
def create_order_shipping_details(order_id: str):
    order = Order.objects.get(id=order_id)
    try:
        order.shipping_detail
    except ObjectDoesNotExist:
        shipping_code = generate_shipping_code()
        qr_filename = f'{order_id}.png'
        directory = settings.MEDIA_ROOT / 'qrcodes'
        if not os.path.exists(directory):
            os.mkdir(directory)

        qr_filepath = directory / qr_filename
        generate_qrcode(qr_filepath, url=settings.QR_URL_TEMPLATE.format(order_id=order_id, code=shipping_code))

        shipping_detail = OrderShipping(order_id=order_id, shipping_code=shipping_code)
        shipping_detail.qrcode_image.name = f'qrcodes/{qr_filename}'
        shipping_detail.save()


@app.task()
def check_paybox_status_for_order(order_id, tries: int = 0):
    order = Order.objects.get(id=order_id)
    if order.status != Order.Status.wait_payment:
        return

    transaction = order.payment_transaction

    if is_success_transaction(transaction):
        order.status = Order.Status.pending
        order.save()
    else:
        if tries < 3:
            tries += 1
            check_paybox_status_for_order.apply_async(eta=now() + timedelta(seconds=15), args=(order_id, tries))
            return

        order.status = Order.Status.payment_rejected
        order.save()
