import logging
import os.path
from datetime import timedelta
from typing import Callable
from uuid import uuid4

from django.conf import settings
from django.core.exceptions import ObjectDoesNotExist
from django.utils.timezone import now

from kaimon.celery import app
from orders.models import Order, OrderConversion, OrderShipping, PaymentTransactionReceipt
from orders.utils import (
    generate_shipping_code, is_success_transaction, get_receipt_usd_price, init_paybox_transaction,
    get_order, init_moneta_invoice, get_invoice_status, real_receipt_moneta_price, real_receipt_usd_price
)
from service.models import Currencies
from service.utils import get_currencies_price_per, generate_qrcode


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
        if tries <= 7:
            tries += 1
            check_paybox_status_for_order.apply_async(eta=now() + timedelta(seconds=5), args=(order_id, tries))
            return

        order.status = Order.Status.payment_rejected
        order.save()


def get_order_tx_data(order_id, on_err_task, tries: int = 1, amount_converter: Callable = None):
    order = get_order(order_id=order_id)
    delay_or_err = 3

    if not order and tries <= 5:
        tries += 1
        on_err_task.apply_async(eta=now() + timedelta(seconds=delay_or_err), args=(order_id, tries))
        logging.error("Not found order with id %s try num %s" % (order_id, tries))
        return
    elif not order and tries > 5:
        logging.error("Sync error of order %s" % order_id)
        return

    if not order.receipts.exists():
        logging.error("order(%s).receipts not found!" % order_id)
        tries += 1
        on_err_task.apply_async(eta=now() + timedelta(seconds=delay_or_err), args=(order_id, tries))
        return

    if not amount_converter:
        amount_converter = get_receipt_usd_price

    receipts_usd_prices = [
        amount_converter(receipt)
        for receipt in order.receipts.only('discount', 'unit_price', 'quantity', 'site_currency').all()
    ]

    if None in receipts_usd_prices:
        logging.error("not all conversions found for order %s!" % order_id)
        tries += 1
        on_err_task.apply_async(eta=now() + timedelta(seconds=delay_or_err), args=(order_id, tries))
        return

    amount = sum(receipts_usd_prices)
    if amount <= 0:
        logging.error("order %s amount equal to zero!" % order_id)
        tries += 1
        on_err_task.apply_async(eta=now() + timedelta(seconds=delay_or_err), args=(order_id, tries))
        return

    return order, amount


@app.task()
def create_order_payment_transaction(order_id, tries: int = 1):
    order, amount = get_order_tx_data(
        order_id,
        on_err_task=create_order_payment_transaction,
        tries=tries,
        amount_converter=real_receipt_usd_price
    )

    transaction_uuid = uuid4()
    paybox_transaction_data = init_paybox_transaction(
        order_id=order_id,
        amount=amount,
        transaction_uuid=transaction_uuid
    )
    check_paybox_status_for_order.apply_async(eta=now() + timedelta(seconds=15), args=(order.id,))
    PaymentTransactionReceipt.objects.create(
        **{
            "order": order,
            "send_amount": amount,
            "uuid": transaction_uuid,
            **paybox_transaction_data
        }
    )


@app.task()
def check_moneta_status(order_id, tries: int, max_tries: int = 10):
    order = Order.objects.get(id=order_id)
    if order.status != Order.Status.wait_payment:
        return

    status = get_invoice_status(order.moneta_invoice)
    save = False
    match status:
        case "WAITING":
            order.status = Order.Status.pending
            save = True
        case "PAID":
            order.status = Order.Status.success
            save = True
        case "EXPIRED":
            order.status = Order.Status.payment_rejected
            save = True

    if save:
        order.save()
    else:
        if tries <= max_tries:
            tries += 1
            check_moneta_status.apply_async(eta=now() + timedelta(seconds=5), args=(order_id, tries))
            return

        order.status = Order.Status.payment_rejected
        order.save()


@app.task()
def create_moneta_invoice(order_id, tries: int = 1, max_tries: int = 10):
    order, amount = get_order_tx_data(
        order_id,
        on_err_task=create_moneta_invoice,
        tries=tries,
        amount_converter=real_receipt_moneta_price
    )

    try:
        init_moneta_invoice(order=order, title="Payment for the order", amount=amount)
    except Exception as err:
        if tries <= max_tries:
            tries += 1
            create_moneta_invoice.apply_async(eta=now() + timedelta(seconds=2), args=(order.id, tries))
        raise err
    else:
        check_moneta_status.apply_async(eta=now() + timedelta(seconds=15), args=(order.id,))
