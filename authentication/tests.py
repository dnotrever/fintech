from datetime import timedelta
from unittest.mock import patch

from django.contrib.auth import get_user_model
from django.core.cache import cache
from django.test import TestCase
from django.utils import timezone
from rest_framework.test import APIClient

from account.models import AccountStatus
from account.services import open_account
from authentication.models import EmailConfirmationToken
from authentication.services import send_confirmation_email
from customer.models import Customer

User = get_user_model()

_PASSWORD = 'Str0ngPassw0rd!'


class LoginRefreshTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(username='jane', password=_PASSWORD)
        self.client = APIClient()

    def test_login_with_valid_credentials_returns_tokens(self):
        response = self.client.post(
            '/auth/login/', {'username': 'jane', 'password': _PASSWORD}, format='json'
        )

        self.assertEqual(response.status_code, 200)
        self.assertIn('access', response.data)
        self.assertIn('refresh', response.data)

    def test_login_with_wrong_password_returns_401(self):
        response = self.client.post(
            '/auth/login/', {'username': 'jane', 'password': 'wrong'}, format='json'
        )

        self.assertEqual(response.status_code, 401)

    def test_refresh_with_valid_token_returns_new_access(self):
        login_response = self.client.post(
            '/auth/login/', {'username': 'jane', 'password': _PASSWORD}, format='json'
        )
        refresh_token = login_response.data['refresh']

        response = self.client.post('/auth/refresh/', {'refresh': refresh_token}, format='json')

        self.assertEqual(response.status_code, 200)
        self.assertIn('access', response.data)


class LogoutTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(username='jane', password=_PASSWORD)
        self.client = APIClient()
        login_response = self.client.post(
            '/auth/login/', {'username': 'jane', 'password': _PASSWORD}, format='json'
        )
        self.access = login_response.data['access']
        self.refresh = login_response.data['refresh']

    def test_logout_without_authentication_returns_401(self):
        response = self.client.post('/auth/logout/', {'refresh': self.refresh}, format='json')

        self.assertEqual(response.status_code, 401)

    def test_logout_blacklists_refresh_token(self):
        self.client.credentials(HTTP_AUTHORIZATION=f'Bearer {self.access}')

        response = self.client.post('/auth/logout/', {'refresh': self.refresh}, format='json')

        self.assertEqual(response.status_code, 205)

        reuse_response = self.client.post('/auth/refresh/', {'refresh': self.refresh}, format='json')
        self.assertEqual(reuse_response.status_code, 401)

    def test_logout_with_invalid_refresh_returns_400(self):
        self.client.credentials(HTTP_AUTHORIZATION=f'Bearer {self.access}')

        response = self.client.post('/auth/logout/', {'refresh': 'not-a-token'}, format='json')

        self.assertEqual(response.status_code, 400)
        self.assertIn('refresh', response.data)


class EmailConfirmationTokenTests(TestCase):
    def test_is_expired_false_when_recently_created(self):
        token = EmailConfirmationToken(created_at=timezone.now())

        self.assertFalse(token.is_expired())

    def test_is_expired_true_after_two_hours(self):
        token = EmailConfirmationToken(created_at=timezone.now() - timedelta(hours=2, seconds=1))

        self.assertTrue(token.is_expired())


class SendConfirmationEmailTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            username='jane', email='jane@example.com', password=_PASSWORD, is_active=False
        )

    @patch('authentication.services.send_email')
    def test_creates_token_and_sends_email(self, mock_send_email):
        send_confirmation_email(self.user)

        self.assertEqual(EmailConfirmationToken.objects.filter(user=self.user).count(), 1)
        mock_send_email.assert_called_once()
        self.assertEqual(mock_send_email.call_args.kwargs['to'], self.user.email)

    @patch('authentication.services.send_email')
    def test_resend_invalidates_previous_unconfirmed_token(self, mock_send_email):
        send_confirmation_email(self.user)
        first_token = EmailConfirmationToken.objects.get(user=self.user).token

        send_confirmation_email(self.user)

        tokens = EmailConfirmationToken.objects.filter(user=self.user)
        self.assertEqual(tokens.count(), 1)
        self.assertNotEqual(tokens.first().token, first_token)

    @patch('authentication.services.send_email', side_effect=RuntimeError('resend is down'))
    def test_send_failure_does_not_raise(self, mock_send_email):
        send_confirmation_email(self.user)

        self.assertEqual(EmailConfirmationToken.objects.filter(user=self.user).count(), 1)


class ConfirmEmailViewTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            username='jane', email='jane@example.com', password=_PASSWORD, is_active=False
        )
        self.customer = Customer.objects.create(
            user=self.user, cpf='52998224725', phone='11999998888', first_name='Jane', last_name='Doe',
        )
        self.account = open_account(customer=self.customer, status=AccountStatus.PENDING)
        self.client = APIClient()

    @patch('authentication.services.send_email')
    def test_valid_token_activates_user_and_account(self, mock_send_email):
        send_confirmation_email(self.user)
        token = EmailConfirmationToken.objects.get(user=self.user).token

        response = self.client.get(f'/auth/confirm/{token}/')

        self.assertEqual(response.status_code, 200)
        self.user.refresh_from_db()
        self.account.refresh_from_db()
        self.assertTrue(self.user.is_active)
        self.assertEqual(self.account.status, AccountStatus.ACTIVE)

    def test_invalid_token_returns_404(self):
        response = self.client.get('/auth/confirm/not-a-real-token/')

        self.assertEqual(response.status_code, 404)

    @patch('authentication.services.send_email')
    def test_already_confirmed_token_returns_400(self, mock_send_email):
        send_confirmation_email(self.user)
        token = EmailConfirmationToken.objects.get(user=self.user).token
        self.client.get(f'/auth/confirm/{token}/')

        response = self.client.get(f'/auth/confirm/{token}/')

        self.assertEqual(response.status_code, 400)

    @patch('authentication.services.send_email')
    def test_expired_token_returns_400(self, mock_send_email):
        send_confirmation_email(self.user)
        confirmation = EmailConfirmationToken.objects.get(user=self.user)
        EmailConfirmationToken.objects.filter(pk=confirmation.pk).update(
            created_at=timezone.now() - timedelta(hours=2, seconds=1)
        )

        response = self.client.get(f'/auth/confirm/{confirmation.token}/')

        self.assertEqual(response.status_code, 400)


class ResendConfirmationViewTests(TestCase):
    def setUp(self):
        cache.clear()
        self.user = User.objects.create_user(
            username='jane', email='jane@example.com', password=_PASSWORD, is_active=False
        )
        self.client = APIClient()

    @patch('authentication.services.send_email')
    def test_resend_for_unconfirmed_user_returns_200_and_creates_token(self, mock_send_email):
        response = self.client.post('/auth/confirm/resend/', {'username': 'jane'}, format='json')

        self.assertEqual(response.status_code, 200)
        self.assertEqual(EmailConfirmationToken.objects.filter(user=self.user).count(), 1)

    def test_resend_for_unknown_username_returns_200_without_creating_token(self):
        response = self.client.post('/auth/confirm/resend/', {'username': 'ghost'}, format='json')

        self.assertEqual(response.status_code, 200)
        self.assertEqual(EmailConfirmationToken.objects.count(), 0)

    @patch('authentication.services.send_email')
    def test_fourth_resend_within_the_hour_is_throttled(self, mock_send_email):
        for _ in range(3):
            response = self.client.post('/auth/confirm/resend/', {'username': 'jane'}, format='json')
            self.assertEqual(response.status_code, 200)

        response = self.client.post('/auth/confirm/resend/', {'username': 'jane'}, format='json')

        self.assertEqual(response.status_code, 429)
