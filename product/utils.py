import hashlib
from django.utils import timezone


def generate_product_id():
    hashlib.sha256()
    timezone.now().timestamp()
    return
