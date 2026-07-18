from dataclasses import FrozenInstanceError
from unittest.mock import patch

from django.contrib.auth import get_user_model
from django.test import TestCase
from rest_framework.test import APIClient

from account.models import Account
from customer.domain import CPF
from customer.models import Address, Customer
from customer.services import register_customer

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


class RegisterCustomerTests(TestCase):
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

        self.assertTrue(User.objects.filter(username='joao123').exists())
        self.assertEqual(Address.objects.filter(customer=customer).count(), 1)
        self.assertTrue(Account.objects.filter(customer=customer).exists())

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


class CustomerCreateViewTests(TestCase):
    def _payload(self, **overrides):
        payload = {
            'username': 'joao123',
            'email': 'joao@example.com',
            'password': 'Str0ngPassw0rd!',
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

    def test_rejects_weak_password(self):
        client = APIClient()

        response = client.post('/customers/', self._payload(password='123', username='weakpw'), format='json')

        self.assertEqual(response.status_code, 400)
        self.assertIn('password', response.data)
