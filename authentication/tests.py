from django.contrib.auth import get_user_model
from django.test import TestCase
from rest_framework.test import APIClient

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
