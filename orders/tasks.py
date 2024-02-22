import logging
from datetime import timedelta, datetime

from django.conf import settings
from django.core.exceptions import ObjectDoesNotExist
from django.utils.timezone import now

from kaimon.celery import app
from orders.models import Order, OrderConversion, OrderShipping
from orders.utils import generate_shipping_code, get_order, qrcode_for_url
from service.clients import PayboxAPI
from service.clients.moneta import MonetaAPI

from service.models import Currencies
from service.utils import get_currencies_price_per


@app.task()
def create_order_conversions(order_id):
    order = get_order(order_id)

    if not order:
        logging.error("Not found order with id %s" % order_id)
        return

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
    order = get_order(order_id)
    if not order:
        logging.error("Not found order with id %s" % order_id)
        return

    try:
        order.shipping_detail
    except ObjectDoesNotExist:
        shipping_code = generate_shipping_code()
        qrcode = qrcode_for_url(order_id, settings.QR_URL_TEMPLATE.format(order_id=order_id, code=shipping_code))
        shipping_detail = OrderShipping(order_id=order_id, shipping_code=shipping_code)
        shipping_detail.qrcode_image.name = qrcode
        shipping_detail.save()


@app.task()
def check_paybox_status_for_order(order_id, tries: int = 0, max_tries: int = 10):
    order = Order.objects.get(id=order_id)
    if order.status != Order.Status.wait_payment:
        return

    payment_client = PayboxAPI(settings.PAYBOX_ID, secret_key=settings.PAYBOX_SECRET_KEY)
    response_data = payment_client.get_transaction_status(
        payment_id=str(order.payment.payment_id),
        order_id=str(order_id),
        salt=settings.PAYBOX_SALT
    )

    if response_data.get("response", {}).get("pg_status", "") == "ok":
        order.status = Order.Status.pending
        order.save()
    else:
        if tries <= max_tries:
            tries += 1
            check_paybox_status_for_order.apply_async(eta=now() + timedelta(seconds=5),
                                                      args=(order_id, tries, max_tries))
            return

        order.status = Order.Status.payment_rejected
        order.save()


@app.task()
def check_moneta_status(order_id, tries: int = 0, max_tries: int = 10):
    order = Order.objects.get(id=order_id)
    if order.status != Order.Status.wait_payment:
        return

    payment = order.payment
    client = MonetaAPI(merchant_id=settings.MONETA_MERCHANT_ID, private_key=settings.MONETA_PRIVATE_KEY)
    status = client.status(payment.payment_id).get("result", {}).get("status", "")

    save = False
    match status:
        case "PAID":
            order.status = Order.Status.pending
            save = True
        case "EXPIRED":
            order.status = Order.Status.payment_rejected
            save = True

    if save:
        order.save()
    else:
        if tries > max_tries:
            order.status = Order.Status.payment_rejected
            order.save()

        if tries < max_tries:
            tries += 1
            check_moneta_status.apply_async(eta=now() + timedelta(seconds=5),
                                            args=(order_id, tries, max_tries))
            return

        # if tries equal to max_tries
        expired = payment.payment_meta.get("expiredBy")
        if not expired:
            order.status = Order.Status.payment_rejected
            order.save()

        try:
            check_paybox_status_for_order.apply_async(
                eta=datetime.strptime(expired, "%Y-%m-%dT%H:%M:%S.%fZ"),
                args=(order_id, tries + 1, max_tries)
            )
        except ValueError:
            order.status = Order.Status.payment_rejected
            order.save()
        else:
            return
