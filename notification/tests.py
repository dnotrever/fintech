from unittest.mock import Mock, patch

from django.conf import settings
from django.test import TestCase

from notification.adapters import ResendEmailAdapter
from notification.services import send_email


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
