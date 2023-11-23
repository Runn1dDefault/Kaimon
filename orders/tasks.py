from uuid import uuid4

from django.conf import settings
from django.core.exceptions import ObjectDoesNotExist

from kaimon.celery import app
from orders.models import Order, OrderConversion, OrderShipping
from orders.utils import generate_shipping_code
from service.models import Currencies
from service.utils import get_currencies_price_per, generate_qrcode


@app.task()
def create_order_conversions(order_id: str):
    order = Order.objects.get(id=order_id)
    new_conversions = []

    main_currency = Currencies.main_currency()
    for conversion in Currencies:
        if conversion != main_currency:
            new_conversions.append(
                OrderConversion(
                    order=order,
                    currenry=conversion,
                    price_per=get_currencies_price_per(main_currency, conversion)
                )
            )

    if new_conversions:
        OrderConversion.objects.bulk_create(new_conversions)


@app.task()
def update_order_shipping_details(order_id: str):
    order = Order.objects.get(id=order_id)
    shipping_weight = 0
    for quantity, avg_weight in order.receipts.values_list('quantity', 'avg_weight'):
        shipping_weight += avg_weight * quantity

    try:
        shipping_detail = order.shipping_detail
    except ObjectDoesNotExist:
        shipping_detail = OrderShipping(order_id=order_id)
        shipping_code = generate_shipping_code()
        shipping_detail.shipping_code = shipping_code
        qr_filename = f'{order_id}.png'
        qr_filepath = settings.MEDIA_ROOT / 'qrcodes' / qr_filename
        generate_qrcode(qr_filepath, url=settings.QR_URL_TEMPLATE.format(order_id=order_id, code=shipping_code))
        shipping_detail.qrcode_image.name = qr_filename

    shipping_detail.shipping_weight = shipping_weight
    shipping_detail.total_price = sum([receipt.total_price for receipt in order.receipts.all()])
    shipping_detail.save()
