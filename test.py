# import qrcode
#
# # Sample order information
# date_of_purchase = "2023-01-01"
# order_contents = "Product 1,  Product 2 x 3"
# total_order_amount = "$"
#
# order_contents = "1."
#
# # Concatenate order information into a string
# f"""
# Customer: John Doe
# Buyer code: JD123
# Date: {date_of_purchase}
# 1. sweetrag:13058716 -
#
# 1500.00 ¥
#
# """
# order_data = f"Buyer: {buyer}\nBuyer Code: {buyer_code}\nDate of Purchase: {date_of_purchase}\nOrder Contents: {order_contents}\nTotal Order Amount: {total_order_amount}"
#
# # Create a QR code instance
# qr = qrcode.QRCode(
#     version=1,
#     error_correction=qrcode.constants.ERROR_CORRECT_L,
#     box_size=10,
#     border=4,
# )
#
# # Add data to the QR code
# qr.add_data(order_data)
# qr.make(fit=True)
#
# # Create an image from the QR code instance
# img = qr.make_image(fill_color="black", back_color="white")
#
# # Save the image
# img.save("order_qr_code.png")
from datetime import datetime

import qrcode

from pdf417 import encode, render_image, render_svg


url = "https://www.example.com"

# Some data to encode
template = "Bayer: {bayer_name}\nBayer Code: {bayer_code}\nEmail: {email}\n" \
           "Date of Purchase: {date}\nProducts:\n{order_contents}\nTotal: {total}"

bayer_name = "John Doe"
bayer_code = "JD1"
email = "jonh_doe@example.com"
date = str(datetime.now())
order_contents = [
    "date27:10055914 x 2 Unit Price: 2530 Site price: 2150.5",
    "date27:10055914 x 2 Unit Price: 2530 Site price: 2150.5",
    "date27:10055914 x 2 Unit Price: 2530 Site price: 2150.5",
    "date27:10055914 x 2 Unit Price: 2530 Site price: 2150.5",
    "date27:10055914 x 2 Unit Price: 2530 Site price: 2150.5",
    "date27:10055914 x 2 Unit Price: 2530 Site price: 2150.5",
    "date27:10055914 x 2 Unit Price: 2530 Site price: 2150.5",
    "date27:10055914 x 2 Unit Price: 2530 Site price: 2150.5",
    "date27:10055914 x 2 Unit Price: 2530 Site price: 2150.5",
    "date27:10055914 x 2 Unit Price: 2530 Site price: 2150.5",
    "date27:10055914 x 2 Unit Price: 2530 Site price: 2150.5",
    "date27:10055914 x 2 Unit Price: 2530 Site price: 2150.5",
    "date27:10055914 x 2 Unit Price: 2530 Site price: 2150.5",
    "date27:10055914 x 2 Unit Price: 2530 Site price: 2150.5",
    "date27:10055914 x 2 Unit Price: 2530 Site price: 2150.5",
    "date27:10055914 x 2 Unit Price: 2530 Site price: 2150.5",
    "date27:10055914 x 2 Unit Price: 2530 Site price: 2150.5",
    "date27:10055914 x 2 Unit Price: 2530 Site price: 2150.5",
    "date27:10055914 x 2 Unit Price: 2530 Site price: 2150.5",
    "date27:10055914 x 2 Unit Price: 2530 Site price: 2150.5",
]
print(len(order_contents))
order_contents = "\n".join(order_contents)
total = "15060"


data = template.format(
    bayer_name=bayer_name,
    bayer_code=bayer_code,
    email=email,
    date=date,
    order_contents=order_contents,
    total=total
)


def generate_qrcode(filepath: str, url: str):
    qr = qrcode.QRCode(version=1, error_correction=qrcode.constants.ERROR_CORRECT_L, box_size=10,
                       border=4)
    qr.add_data(url)
    qr.make(fit=True)
    img = qr.make_image(fill_color="black", back_color="white")
    img.save(filepath)


# print(data)
# Convert to code words
# codes = encode(data)
# # image = render_image(codes)  # Pillow Image object
# # image.save('barcode.jpg')
# #
# # # Generate barcode as SVG
# svg = render_svg(codes)  # ElementTree object
# svg.write("barcode.svg")
