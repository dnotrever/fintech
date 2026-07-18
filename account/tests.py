from django.contrib.auth import get_user_model
from django.test import TestCase

from account.models import Account, AccountType
from account.services import AccountNumberGenerationError, open_account
from customer.models import Customer

User = get_user_model()


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
