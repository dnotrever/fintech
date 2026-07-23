from unittest.mock import Mock, patch

from celery.exceptions import Retry
from django.conf import settings
from django.test import TestCase

from notification.adapters import _TIMEOUT_SECONDS, ResendEmailAdapter
from notification.services import send_email
from notification.tasks import send_email_task


class SendEmailTests(TestCase):
    def test_uses_injected_channel(self):
        fake_channel = Mock()

        send_email(to='jane@example.com', subject='Hi', body='Hello', channel=fake_channel)

        fake_channel.send.assert_called_once_with(to='jane@example.com', subject='Hi', body='Hello')

    def test_uses_default_channel_when_none_given(self):
        with patch('notification.services._default_channel') as fake_default:
            send_email(to='jane@example.com', subject='Hi', body='Hello')

        fake_default.send.assert_called_once_with(to='jane@example.com', subject='Hi', body='Hello')


class ResendEmailAdapterTests(TestCase):
    @patch('notification.adapters.resend')
    def test_send_calls_resend_emails_send_with_expected_payload(self, mock_resend):
        adapter = ResendEmailAdapter()

        adapter.send(to='jane@example.com', subject='Hi', body='<p>Hello</p>')

        mock_resend.Emails.send.assert_called_once_with({
            'from': settings.DEFAULT_FROM_EMAIL,
            'to': ['jane@example.com'],
            'subject': 'Hi',
            'html': '<p>Hello</p>',
        })

    @patch('notification.adapters.RequestsClient')
    @patch('notification.adapters.resend')
    def test_init_configures_default_http_client_with_timeout(self, mock_resend, mock_requests_client):
        ResendEmailAdapter()

        mock_requests_client.assert_called_once_with(timeout=_TIMEOUT_SECONDS)
        self.assertEqual(mock_resend.default_http_client, mock_requests_client.return_value)


class SendEmailTaskTests(TestCase):
    @patch('notification.tasks.send_email')
    def test_calls_send_email_with_given_arguments(self, mock_send_email):
        send_email_task(to='jane@example.com', subject='Hi', body='Hello')

        mock_send_email.assert_called_once_with(to='jane@example.com', subject='Hi', body='Hello')

    @patch('notification.tasks.send_email', side_effect=RuntimeError('resend is down'))
    def test_retries_via_self_retry_on_failure(self, mock_send_email):
        with self.assertRaises(Retry):
            send_email_task.apply(
                kwargs={'to': 'jane@example.com', 'subject': 'Hi', 'body': 'Hello'}, throw=True
            )

        mock_send_email.assert_called_once()
