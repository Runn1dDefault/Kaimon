import unittest
from unittest.mock import patch

from .paybox import PayboxAPI


class TestPayboxAPI(unittest.TestCase):
    def setUp(self):
        self.paybox = PayboxAPI(merchant_id="553276", secret_key="pqnt5T6sX6E8bCJ6")

    def tearDown(self):
        self.paybox.session.close()

    @patch("service.clients.PayboxAPI.post")
    def test_init_transaction(self, mock_post):
        mock_response_data = {'response': {'pg_redirect_url': 'mock_url', 'pg_payment_id': 'mock_payment_id'}}
        mock_post.return_value = mock_response_data

        order_id = "2"
        amount = "10.5"
        description = "Test description"
        salt = "kaimono.vip_test"
        currency = "USD"
        result_url = "https://example.com/result"
        success_url = "https://example.com/success"
        failure_url = "https://example.com/failure"
        resp_data = self.paybox.init_transaction(
            order_id=order_id,
            amount=amount,
            description=description,
            salt=salt,
            currency=currency,
            result_url=result_url,
            success_url=success_url,
            failure_url=failure_url,
            test_param="value"
        )
        mock_post.assert_called()
        self.assertEqual(resp_data, mock_post.return_value)
        self.assertIsNotNone(resp_data.get("response"))
        self.assertIsInstance(resp_data.get("response"), dict)
        self.assertIn("pg_redirect_url", resp_data.get("response"))
        self.assertIn("pg_payment_id", resp_data.get("response"))

    @patch("service.clients.PayboxAPI.post")
    def test_get_transaction_status(self, mock_post):
        mock_post.return_value = {"response": {"pg_status": "ok"}}
        payment_id = "1066603760"
        order_id = "24"
        salt = "kaimono.vip_test"

        resp_data = self.paybox.get_transaction_status(
            payment_id=payment_id,
            order_id=order_id,
            salt=salt
        )

        mock_post.assert_called()
        self.assertEqual(resp_data, mock_post.return_value)
        self.assertIsNotNone(resp_data.get("response"))
        self.assertIsInstance(resp_data.get("response"), dict)
        self.assertIn("pg_status", resp_data.get("response"))
        self.assertIn(resp_data["response"]["pg_status"], ("ok", "error", "rejected"))


if __name__ == "__main__":
    unittest.main()
