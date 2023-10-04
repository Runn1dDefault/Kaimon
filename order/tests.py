from django.urls import reverse
from rest_framework import status
from rest_framework.test import APITestCase, URLPatternsTestCase

from .urls import urlpatterns


class OrderTests(APITestCase, URLPatternsTestCase):
    urlpatterns = urlpatterns

    def test_create_order(self):
        """
        Ensure we can create a new account object.
        """
        url = reverse('account-list')
        response = self.client.get(url, format='json')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 1)
