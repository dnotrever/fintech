from dataclasses import FrozenInstanceError
from decimal import Decimal
from unittest.mock import patch

from django.contrib.auth import get_user_model
from django.test import TestCase
from rest_framework.test import APIClient

from account.models import Account, AccountStatus, Transaction
from account.services import deposit
from customer.domain import CPF, Phone
from customer.models import Address, Customer
from customer.services import delete_user_completely, register_customer

User = get_user_model()

VALID_CPF = '52998224725'

_ADDRESS = {
    'number': '100',
    'street': 'Av. Paulista',
    'city': 'São Paulo',
    'state': 'SP',
    'zip_code': '01310000',
}


class CPFTests(TestCase):
    def test_accepts_valid_cpf(self):
        cpf = CPF(VALID_CPF)

        self.assertEqual(str(cpf), VALID_CPF)

    def test_rejects_invalid_check_digits(self):
        with self.assertRaises(ValueError):
            CPF('12345678900')

    def test_rejects_all_repeated_digits(self):
        with self.assertRaises(ValueError):
            CPF('11111111111')

    def test_rejects_wrong_length(self):
        with self.assertRaises(ValueError):
            CPF('123456789')

    def test_is_immutable(self):
        cpf = CPF(VALID_CPF)

        with self.assertRaises(FrozenInstanceError):
            cpf.value = '00000000000'

    def test_equality_by_value(self):
        self.assertEqual(CPF(VALID_CPF), CPF(VALID_CPF))


class PhoneTests(TestCase):
    def test_accepts_valid_mobile(self):
        phone = Phone('11999998888')

        self.assertEqual(str(phone), '11999998888')

    def test_accepts_valid_landline(self):
        phone = Phone('1133334444')

        self.assertEqual(str(phone), '1133334444')

    def test_rejects_invalid_ddd(self):
        with self.assertRaises(ValueError):
            Phone('20999998888')

    def test_rejects_mobile_without_leading_nine(self):
        with self.assertRaises(ValueError):
            Phone('11899998888')

    def test_rejects_landline_with_invalid_leading_digit(self):
        with self.assertRaises(ValueError):
            Phone('1199998888')

    def test_rejects_wrong_length(self):
        with self.assertRaises(ValueError):
            Phone('119999988')

    def test_rejects_non_digit_characters(self):
        with self.assertRaises(ValueError):
            Phone('11999-98888')

    def test_is_immutable(self):
        phone = Phone('11999998888')

        with self.assertRaises(FrozenInstanceError):
            phone.value = '11888887777'

    def test_equality_by_value(self):
        self.assertEqual(Phone('11999998888'), Phone('11999998888'))


class CustomerModelTests(TestCase):
    def test_rejects_invalid_cpf_on_save(self):
        user = User.objects.create_user(username='joao123', email='joao@example.com', password='pw')

        with self.assertRaises(ValueError):
            Customer.objects.create(
                user=user,
                cpf='12345678900',
                phone='11999998888',
                first_name='João',
                last_name='Silva',
            )

    def test_rejects_invalid_phone_on_save(self):
        user = User.objects.create_user(username='joao123', email='joao@example.com', password='pw')

        with self.assertRaises(ValueError):
            Customer.objects.create(
                user=user,
                cpf=VALID_CPF,
                phone='20999998888',
                first_name='João',
                last_name='Silva',
            )


class RegisterCustomerTests(TestCase):
    def setUp(self):
        patcher = patch('customer.services.send_confirmation_email')
        self.mock_send_confirmation_email = patcher.start()
        self.addCleanup(patcher.stop)

    def test_creates_user_customer_address_and_account(self):
        customer = register_customer(
            username='joao123',
            email='joao@example.com',
            password='Str0ngPassw0rd!',
            cpf=VALID_CPF,
            phone='11999998888',
            first_name='João',
            last_name='Silva',
            birth_date=None,
            address=_ADDRESS,
        )

        user = User.objects.get(username='joao123')
        self.assertFalse(user.is_active)
        self.assertEqual(Address.objects.filter(customer=customer).count(), 1)
        account = Account.objects.get(customer=customer)
        self.assertEqual(account.status, AccountStatus.PENDING)
        self.mock_send_confirmation_email.assert_called_once_with(user)

    def test_rejects_invalid_phone(self):
        with self.assertRaises(ValueError):
            register_customer(
                username='joao123',
                email='joao@example.com',
                password='Str0ngPassw0rd!',
                cpf=VALID_CPF,
                phone='20999998888',
                first_name='João',
                last_name='Silva',
                birth_date=None,
                address=_ADDRESS,
            )

    def test_compensates_when_account_opening_fails(self):
        with self.assertRaises(RuntimeError):
            with patch('customer.services.open_account', side_effect=RuntimeError('boom')):
                register_customer(
                    username='joao123',
                    email='joao@example.com',
                    password='Str0ngPassw0rd!',
                    cpf=VALID_CPF,
                    phone='11999998888',
                    first_name='João',
                    last_name='Silva',
                    birth_date=None,
                    address=_ADDRESS,
                )

        self.assertFalse(User.objects.filter(username='joao123').exists())
        self.assertFalse(Customer.objects.filter(cpf=VALID_CPF).exists())


class DeleteUserCompletelyTests(TestCase):
    def setUp(self):
        patcher = patch('customer.services.send_confirmation_email')
        patcher.start()
        self.addCleanup(patcher.stop)

    def test_deletes_user_customer_address_and_account(self):
        customer = register_customer(
            username='joao123',
            email='joao@example.com',
            password='Str0ngPassw0rd!',
            cpf=VALID_CPF,
            phone='11999998888',
            first_name='João',
            last_name='Silva',
            birth_date=None,
            address=_ADDRESS,
        )
        user = User.objects.get(username='joao123')

        delete_user_completely(user=user)

        self.assertFalse(User.objects.filter(username='joao123').exists())
        self.assertFalse(Customer.objects.filter(cpf=VALID_CPF).exists())
        self.assertFalse(Address.objects.filter(customer=customer).exists())
        self.assertFalse(Account.objects.filter(customer=customer).exists())

    def test_deletes_transactions_before_account_despite_protect(self):
        customer = register_customer(
            username='joao123',
            email='joao@example.com',
            password='Str0ngPassw0rd!',
            cpf=VALID_CPF,
            phone='11999998888',
            first_name='João',
            last_name='Silva',
            birth_date=None,
            address=_ADDRESS,
        )
        account = Account.objects.get(customer=customer)
        account.status = AccountStatus.ACTIVE
        account.save()
        deposit(account=account, amount=Decimal('50.00'), idempotency_key='key-1')
        user = User.objects.get(username='joao123')

        delete_user_completely(user=user)

        self.assertFalse(User.objects.filter(username='joao123').exists())
        self.assertFalse(Transaction.objects.filter(account=account).exists())

    def test_deletes_user_without_customer(self):
        user = User.objects.create_user(username='staffuser', password='Str0ngPassw0rd!')

        delete_user_completely(user=user)

        self.assertFalse(User.objects.filter(username='staffuser').exists())

    def test_deletes_customer_without_account(self):
        user = User.objects.create_user(username='joao123', email='joao@example.com', password='Str0ngPassw0rd!')
        customer = Customer.objects.create(
            user=user, cpf=VALID_CPF, phone='11999998888', first_name='João', last_name='Silva',
        )

        delete_user_completely(user=user)

        self.assertFalse(User.objects.filter(username='joao123').exists())
        self.assertFalse(Customer.objects.filter(pk=customer.pk).exists())


class CustomerCreateViewTests(TestCase):
    def setUp(self):
        patcher = patch('customer.services.send_confirmation_email')
        self.mock_send_confirmation_email = patcher.start()
        self.addCleanup(patcher.stop)

    def _payload(self, **overrides):
        payload = {
            'username': 'joao123',
            'email': 'joao@example.com',
            'password': 'Str0ngPassw0rd!',
            'password_confirm': 'Str0ngPassw0rd!',
            'cpf': VALID_CPF,
            'phone': '11999998888',
            'first_name': 'João',
            'last_name': 'Silva',
            'birth_date': '1990-05-20',
            'address': dict(_ADDRESS),
        }
        payload.update(overrides)
        return payload

    def test_registers_customer_with_linked_account(self):
        client = APIClient()

        response = client.post('/customers/', self._payload(), format='json')

        self.assertEqual(response.status_code, 201)
        self.assertIsNotNone(response.data['account'])
        self.assertEqual(response.data['account']['account_type'], 'checking')
        self.assertEqual(response.data['account']['status'], 'pending')
        self.assertEqual(len(response.data['addresses']), 1)

    def test_rejects_duplicate_username(self):
        client = APIClient()
        client.post('/customers/', self._payload(), format='json')

        response = client.post('/customers/', self._payload(email='other@example.com'), format='json')

        self.assertEqual(response.status_code, 400)
        self.assertIn('username', response.data)

    def test_rejects_invalid_cpf_check_digits(self):
        client = APIClient()

        response = client.post('/customers/', self._payload(cpf='12345678900'), format='json')

        self.assertEqual(response.status_code, 400)
        self.assertIn('cpf', response.data)

    def test_rejects_invalid_phone(self):
        client = APIClient()

        response = client.post('/customers/', self._payload(phone='20999998888'), format='json')

        self.assertEqual(response.status_code, 400)
        self.assertIn('phone', response.data)

    def test_rejects_weak_password(self):
        client = APIClient()

        response = client.post(
            '/customers/',
            self._payload(password='123', password_confirm='123', username='weakpw'),
            format='json',
        )

        self.assertEqual(response.status_code, 400)
        self.assertIn('password', response.data)

    def test_rejects_mismatched_password_confirmation(self):
        client = APIClient()

        response = client.post(
            '/customers/', self._payload(password_confirm='Different123!'), format='json'
        )

        self.assertEqual(response.status_code, 400)
        self.assertIn('password_confirm', response.data)

    def test_registration_triggers_confirmation_email(self):
        client = APIClient()

        client.post('/customers/', self._payload(), format='json')

        self.mock_send_confirmation_email.assert_called_once()
