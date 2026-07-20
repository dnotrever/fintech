from decimal import Decimal

from django.contrib.auth import get_user_model
from django.test import TestCase
from rest_framework.test import APIClient

from account.models import Account, AccountStatus, AccountType, InvalidAccountStatusTransitionError
from account.services import AccountNumberGenerationError, open_account
from customer.models import Customer

User = get_user_model()

_PASSWORD = 'Str0ngPassw0rd!'


def _create_customer(*, username: str = 'jane', cpf: str = '12345678901') -> Customer:
    user = User.objects.create_user(
        username=username, email=f'{username}@example.com', password='Str0ngPassw0rd!'
    )
    return Customer.objects.create(
        user=user, cpf=cpf, phone='11999998888', first_name='Jane', last_name='Doe',
    )


class OpenAccountTests(TestCase):
    def test_creates_checking_account_for_customer(self):
        customer = _create_customer()

        account = open_account(customer=customer)

        self.assertEqual(account.customer, customer)
        self.assertEqual(account.account_type, AccountType.CHECKING)
        self.assertEqual(account.agency, '00001')
        self.assertEqual(len(account.account_number), 6)
        self.assertTrue(Account.objects.filter(pk=account.pk).exists())

    def test_uses_injected_number_generator(self):
        customer = _create_customer()

        account = open_account(customer=customer, number_generator=lambda: '424242')

        self.assertEqual(account.account_number, '424242')

    def test_raises_when_number_generator_keeps_colliding(self):
        customer = _create_customer()
        open_account(customer=customer, number_generator=lambda: '111111')
        other_customer = _create_customer(username='john', cpf='98765432100')

        with self.assertRaises(AccountNumberGenerationError):
            open_account(customer=other_customer, number_generator=lambda: '111111')


class OpenAccountStatusTests(TestCase):
    def test_defaults_to_active_status(self):
        customer = _create_customer()

        account = open_account(customer=customer)

        self.assertEqual(account.status, AccountStatus.ACTIVE)

    def test_accepts_explicit_pending_status(self):
        customer = _create_customer()

        account = open_account(customer=customer, status=AccountStatus.PENDING)

        self.assertEqual(account.status, AccountStatus.PENDING)


class AccountStatusTransitionTests(TestCase):
    def test_pending_can_transition_to_active(self):
        customer = _create_customer()
        account = open_account(customer=customer, status=AccountStatus.PENDING)

        account.change_status(AccountStatus.ACTIVE)

        self.assertEqual(account.status, AccountStatus.ACTIVE)

    def test_pending_cannot_transition_to_blocked(self):
        customer = _create_customer()
        account = open_account(customer=customer, status=AccountStatus.PENDING)

        with self.assertRaises(InvalidAccountStatusTransitionError):
            account.change_status(AccountStatus.BLOCKED)


class AccountBalanceViewTests(TestCase):
    def setUp(self):
        customer = _create_customer()
        self.account = open_account(customer=customer, status=AccountStatus.ACTIVE)
        self.account.balance = Decimal('150.00')
        self.account.save()
        self.client = APIClient()

    def _login(self):
        response = self.client.post(
            '/auth/login/', {'username': 'jane', 'password': _PASSWORD}, format='json'
        )
        return response.data['access']

    def test_authenticated_customer_gets_own_balance(self):
        access = self._login()
        self.client.credentials(HTTP_AUTHORIZATION=f'Bearer {access}')

        response = self.client.get('/accounts/balance/')

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data['balance'], '150.00')
        self.assertEqual(response.data['currency'], 'BRL')

    def test_unauthenticated_request_returns_401(self):
        response = self.client.get('/accounts/balance/')

        self.assertEqual(response.status_code, 401)
