from datetime import date, timedelta
from decimal import Decimal
from unittest.mock import patch

from django.contrib.auth import get_user_model
from django.db import IntegrityError
from django.test import TestCase
from django.utils import timezone
from rest_framework.test import APIClient

from account.models import (
    Account,
    AccountStatus,
    AccountType,
    InvalidAccountStatusTransitionError,
    Transaction,
    TransactionStatus,
    TransactionType,
)
from account.selectors import get_statement
from account.serializers import StatementFilterSerializer
from account.services import AccountNumberGenerationError, IdempotencyKeyConflictError, deposit, open_account
from customer.models import Customer

User = get_user_model()

_PASSWORD = 'Str0ngPassw0rd!'


def _create_customer(*, username: str = 'jane', cpf: str = '11144477735') -> Customer:
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
        other_customer = _create_customer(username='john', cpf='22255588846')

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


class DepositViewTests(TestCase):
    def setUp(self):
        customer = _create_customer()
        self.account = open_account(customer=customer, status=AccountStatus.ACTIVE)
        self.client = APIClient()

    def _login(self):
        response = self.client.post(
            '/auth/login/', {'username': 'jane', 'password': _PASSWORD}, format='json'
        )
        return response.data['access']

    def test_authenticated_deposit_credits_account_and_returns_201(self):
        access = self._login()
        self.client.credentials(HTTP_AUTHORIZATION=f'Bearer {access}')

        response = self.client.post(
            '/accounts/deposit/',
            {'amount': '100.00'},
            format='json',
            HTTP_IDEMPOTENCY_KEY='key-1',
        )

        self.assertEqual(response.status_code, 201)
        self.assertEqual(response.data['amount'], '100.00')
        self.assertEqual(response.data['balance_after'], '100.00')
        self.assertEqual(response.data['status'], 'completed')
        self.account.refresh_from_db()
        self.assertEqual(self.account.balance, Decimal('100.00'))

    def test_unauthenticated_deposit_returns_401(self):
        response = self.client.post(
            '/accounts/deposit/', {'amount': '100.00'}, format='json', HTTP_IDEMPOTENCY_KEY='key-1'
        )

        self.assertEqual(response.status_code, 401)

    def test_missing_idempotency_key_header_returns_400(self):
        access = self._login()
        self.client.credentials(HTTP_AUTHORIZATION=f'Bearer {access}')

        response = self.client.post('/accounts/deposit/', {'amount': '100.00'}, format='json')

        self.assertEqual(response.status_code, 400)
        self.account.refresh_from_db()
        self.assertEqual(self.account.balance, Decimal('0.00'))

    def test_non_positive_amount_returns_400(self):
        access = self._login()
        self.client.credentials(HTTP_AUTHORIZATION=f'Bearer {access}')

        response = self.client.post(
            '/accounts/deposit/', {'amount': '0.00'}, format='json', HTTP_IDEMPOTENCY_KEY='key-1'
        )

        self.assertEqual(response.status_code, 400)

    def test_replaying_same_key_and_amount_returns_201_without_double_credit(self):
        access = self._login()
        self.client.credentials(HTTP_AUTHORIZATION=f'Bearer {access}')
        first = self.client.post(
            '/accounts/deposit/', {'amount': '100.00'}, format='json', HTTP_IDEMPOTENCY_KEY='key-1'
        )

        second = self.client.post(
            '/accounts/deposit/', {'amount': '100.00'}, format='json', HTTP_IDEMPOTENCY_KEY='key-1'
        )

        self.assertEqual(second.status_code, 201)
        self.assertEqual(second.data['id'], first.data['id'])
        self.account.refresh_from_db()
        self.assertEqual(self.account.balance, Decimal('100.00'))

    def test_replaying_same_key_with_different_amount_returns_409(self):
        access = self._login()
        self.client.credentials(HTTP_AUTHORIZATION=f'Bearer {access}')
        self.client.post(
            '/accounts/deposit/', {'amount': '100.00'}, format='json', HTTP_IDEMPOTENCY_KEY='key-1'
        )

        response = self.client.post(
            '/accounts/deposit/', {'amount': '50.00'}, format='json', HTTP_IDEMPOTENCY_KEY='key-1'
        )

        self.assertEqual(response.status_code, 409)
        self.account.refresh_from_db()
        self.assertEqual(self.account.balance, Decimal('100.00'))


class AccountStatementViewTests(TestCase):
    def setUp(self):
        customer = _create_customer()
        self.account = open_account(customer=customer, status=AccountStatus.ACTIVE)
        self.client = APIClient()

    def _login(self):
        response = self.client.post(
            '/auth/login/', {'username': 'jane', 'password': _PASSWORD}, format='json'
        )
        return response.data['access']

    def _create_transaction(self, *, account, created_at, idempotency_key):
        txn = Transaction.objects.create(
            account=account,
            type=TransactionType.DEPOSIT,
            amount=Decimal('10.00'),
            balance_after=Decimal('10.00'),
            status=TransactionStatus.COMPLETED,
            idempotency_key=idempotency_key,
        )
        Transaction.objects.filter(pk=txn.pk).update(created_at=created_at)
        return txn

    def test_authenticated_customer_gets_paginated_statement(self):
        access = self._login()
        self.client.credentials(HTTP_AUTHORIZATION=f'Bearer {access}')
        self._create_transaction(account=self.account, created_at=timezone.now(), idempotency_key='key-1')

        response = self.client.get('/accounts/statement/')

        self.assertEqual(response.status_code, 200)
        self.assertIn('count', response.data)
        self.assertIn('results', response.data)
        self.assertEqual(response.data['count'], 1)

    def test_unauthenticated_request_returns_401(self):
        response = self.client.get('/accounts/statement/')

        self.assertEqual(response.status_code, 401)

    def test_inverted_date_range_returns_400(self):
        access = self._login()
        self.client.credentials(HTTP_AUTHORIZATION=f'Bearer {access}')

        response = self.client.get('/accounts/statement/', {
            'start_date': date.today().isoformat(),
            'end_date': (date.today() - timedelta(days=1)).isoformat(),
        })

        self.assertEqual(response.status_code, 400)

    def test_does_not_leak_transactions_from_other_accounts(self):
        other_customer = _create_customer(username='john', cpf='22255588846')
        other_account = open_account(customer=other_customer, status=AccountStatus.ACTIVE)
        self._create_transaction(account=other_account, created_at=timezone.now(), idempotency_key='other-key')

        access = self._login()
        self.client.credentials(HTTP_AUTHORIZATION=f'Bearer {access}')

        response = self.client.get('/accounts/statement/')

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data['count'], 0)


class TransactionModelTests(TestCase):
    def setUp(self):
        customer = _create_customer()
        self.account = open_account(customer=customer, status=AccountStatus.ACTIVE)

    def test_creates_transaction_with_expected_fields(self):
        txn = Transaction.objects.create(
            account=self.account,
            type=TransactionType.DEPOSIT,
            amount=Decimal('100.00'),
            balance_after=Decimal('100.00'),
            status=TransactionStatus.COMPLETED,
            idempotency_key='key-1',
        )

        self.assertEqual(txn.account, self.account)
        self.assertEqual(txn.type, TransactionType.DEPOSIT)
        self.assertEqual(txn.amount, Decimal('100.00'))
        self.assertEqual(txn.balance_after, Decimal('100.00'))
        self.assertEqual(txn.status, TransactionStatus.COMPLETED)

    def test_rejects_duplicate_idempotency_key_for_same_account(self):
        Transaction.objects.create(
            account=self.account,
            type=TransactionType.DEPOSIT,
            amount=Decimal('50.00'),
            balance_after=Decimal('50.00'),
            status=TransactionStatus.COMPLETED,
            idempotency_key='dup-key',
        )

        with self.assertRaises(IntegrityError):
            Transaction.objects.create(
                account=self.account,
                type=TransactionType.DEPOSIT,
                amount=Decimal('25.00'),
                balance_after=Decimal('75.00'),
                status=TransactionStatus.COMPLETED,
                idempotency_key='dup-key',
            )


class GetStatementTests(TestCase):
    def setUp(self):
        customer = _create_customer()
        self.account = open_account(customer=customer, status=AccountStatus.ACTIVE)
        other_customer = _create_customer(username='john', cpf='22255588846')
        self.other_account = open_account(customer=other_customer, status=AccountStatus.ACTIVE)

    def _create_transaction(self, *, account, created_at, idempotency_key):
        txn = Transaction.objects.create(
            account=account,
            type=TransactionType.DEPOSIT,
            amount=Decimal('10.00'),
            balance_after=Decimal('10.00'),
            status=TransactionStatus.COMPLETED,
            idempotency_key=idempotency_key,
        )
        Transaction.objects.filter(pk=txn.pk).update(created_at=created_at)
        txn.refresh_from_db()
        return txn

    def test_returns_only_transactions_within_range_for_the_account(self):
        today = timezone.now()
        in_range = self._create_transaction(account=self.account, created_at=today, idempotency_key='in-range')
        out_of_range = self._create_transaction(
            account=self.account, created_at=today - timedelta(days=10), idempotency_key='out-of-range'
        )
        other_accounts_txn = self._create_transaction(
            account=self.other_account, created_at=today, idempotency_key='other-account'
        )

        result = list(get_statement(
            account=self.account, start_date=today.date() - timedelta(days=1), end_date=today.date()
        ))

        self.assertIn(in_range, result)
        self.assertNotIn(out_of_range, result)
        self.assertNotIn(other_accounts_txn, result)

    def test_orders_by_most_recent_first(self):
        today = timezone.now()
        older = self._create_transaction(
            account=self.account, created_at=today - timedelta(days=1), idempotency_key='older'
        )
        newer = self._create_transaction(account=self.account, created_at=today, idempotency_key='newer')

        result = list(get_statement(
            account=self.account, start_date=today.date() - timedelta(days=7), end_date=today.date()
        ))

        self.assertEqual(result, [newer, older])


class StatementFilterSerializerTests(TestCase):
    def test_defaults_to_last_seven_days_when_no_params(self):
        serializer = StatementFilterSerializer(data={})
        serializer.is_valid(raise_exception=True)

        today = date.today()
        self.assertEqual(serializer.validated_data['end_date'], today)
        self.assertEqual(serializer.validated_data['start_date'], today - timedelta(days=7))

    def test_defaults_end_date_to_today_when_only_start_date_given(self):
        start = date.today() - timedelta(days=3)
        serializer = StatementFilterSerializer(data={'start_date': start.isoformat()})
        serializer.is_valid(raise_exception=True)

        self.assertEqual(serializer.validated_data['start_date'], start)
        self.assertEqual(serializer.validated_data['end_date'], date.today())

    def test_defaults_start_date_to_seven_days_before_end_date_when_only_end_date_given(self):
        end = date.today() - timedelta(days=2)
        serializer = StatementFilterSerializer(data={'end_date': end.isoformat()})
        serializer.is_valid(raise_exception=True)

        self.assertEqual(serializer.validated_data['end_date'], end)
        self.assertEqual(serializer.validated_data['start_date'], end - timedelta(days=7))

    def test_rejects_start_date_after_end_date(self):
        serializer = StatementFilterSerializer(data={
            'start_date': date.today().isoformat(),
            'end_date': (date.today() - timedelta(days=1)).isoformat(),
        })

        self.assertFalse(serializer.is_valid())
        self.assertIn('start_date', serializer.errors)


class DepositServiceTests(TestCase):
    def setUp(self):
        customer = _create_customer()
        self.account = open_account(customer=customer, status=AccountStatus.ACTIVE)

    def test_credits_account_and_creates_completed_transaction(self):
        txn = deposit(account=self.account, amount=Decimal('100.00'), idempotency_key='key-1')

        self.account.refresh_from_db()
        self.assertEqual(self.account.balance, Decimal('100.00'))
        self.assertEqual(txn.amount, Decimal('100.00'))
        self.assertEqual(txn.balance_after, Decimal('100.00'))
        self.assertEqual(txn.status, TransactionStatus.COMPLETED)
        self.assertEqual(txn.type, TransactionType.DEPOSIT)
        self.assertEqual(txn.idempotency_key, 'key-1')

    def test_replaying_same_key_and_amount_does_not_double_credit(self):
        first = deposit(account=self.account, amount=Decimal('100.00'), idempotency_key='key-1')

        second = deposit(account=self.account, amount=Decimal('100.00'), idempotency_key='key-1')

        self.account.refresh_from_db()
        self.assertEqual(second.id, first.id)
        self.assertEqual(self.account.balance, Decimal('100.00'))
        self.assertEqual(Transaction.objects.filter(account=self.account).count(), 1)

    def test_recovers_from_integrity_error_on_concurrent_same_key_deposit(self):
        existing = Transaction.objects.create(
            account=self.account,
            type=TransactionType.DEPOSIT,
            amount=Decimal('100.00'),
            balance_after=Decimal('100.00'),
            status=TransactionStatus.COMPLETED,
            idempotency_key='race-key',
        )

        with patch('account.services.Transaction.objects.filter') as mock_filter:
            mock_filter.return_value.first.return_value = None
            result = deposit(account=self.account, amount=Decimal('100.00'), idempotency_key='race-key')

        self.assertEqual(result.id, existing.id)
        self.assertEqual(Transaction.objects.filter(account=self.account, idempotency_key='race-key').count(), 1)

    def test_replaying_same_key_with_different_amount_raises_conflict(self):
        deposit(account=self.account, amount=Decimal('100.00'), idempotency_key='key-1')

        with self.assertRaises(IdempotencyKeyConflictError):
            deposit(account=self.account, amount=Decimal('50.00'), idempotency_key='key-1')

        self.account.refresh_from_db()
        self.assertEqual(self.account.balance, Decimal('100.00'))
