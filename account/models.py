import uuid
from decimal import Decimal

from customer.models import Customer
from django.db import models


class AccountType(models.TextChoices):
    CHECKING = 'checking', 'Checking'
    SAVINGS = 'savings', 'Savings'


class AccountStatus(models.TextChoices):
    PENDING = 'pending', 'Pending'
    ACTIVE = 'active', 'Active'
    BLOCKED = 'blocked', 'Blocked'
    CLOSED = 'closed', 'Closed'


class Account(models.Model):

    _ALLOWED_STATUS_TRANSITIONS = {
        AccountStatus.PENDING: {AccountStatus.ACTIVE},
        AccountStatus.ACTIVE: {AccountStatus.BLOCKED, AccountStatus.CLOSED},
        AccountStatus.BLOCKED: {AccountStatus.ACTIVE, AccountStatus.CLOSED},
        AccountStatus.CLOSED: set(),
    }

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    customer = models.OneToOneField(Customer, on_delete=models.PROTECT, related_name='account')

    account_number = models.CharField(max_length=6, unique=True)
    agency = models.CharField(max_length=5, blank=False)

    account_type = models.CharField(max_length=10, choices=AccountType.choices, default=AccountType.CHECKING)
    status = models.CharField(max_length=10, choices=AccountStatus.choices, default=AccountStatus.ACTIVE)

    balance = models.DecimalField(max_digits=14, decimal_places=2, default=0)
    currency = models.CharField(max_length=3, default='BRL')

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'account'

    def __str__(self) -> str:
        return f'{self.agency}/{self.account_number}'

    def credit(self, amount: Decimal) -> None:
        if amount <= 0:
            raise ValueError('Credit amount must be positive.')
        self.balance += amount

    def debit(self, amount: Decimal) -> None:
        if amount <= 0:
            raise ValueError('Debit amount must be positive.')
        if amount > self.balance:
            raise InsufficientFundsError(f'Account {self} has insufficient funds.')
        self.balance -= amount

    def change_status(self, new_status: AccountStatus) -> None:
        allowed = self._ALLOWED_STATUS_TRANSITIONS[self.status]
        if new_status not in allowed:
            raise InvalidAccountStatusTransitionError(
                f'Cannot transition account from {self.status} to {new_status}.'
            )
        self.status = new_status


class InsufficientFundsError(Exception):
    pass


class InvalidAccountStatusTransitionError(Exception):
    pass


class TransactionType(models.TextChoices):
    DEPOSIT = 'deposit', 'Deposit'


class TransactionStatus(models.TextChoices):
    PENDING = 'pending', 'Pending'
    COMPLETED = 'completed', 'Completed'
    FAILED = 'failed', 'Failed'


class Transaction(models.Model):
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    account = models.ForeignKey(Account, on_delete=models.PROTECT, related_name='transactions')

    type = models.CharField(max_length=10, choices=TransactionType.choices)
    amount = models.DecimalField(max_digits=14, decimal_places=2)
    balance_after = models.DecimalField(max_digits=14, decimal_places=2)
    status = models.CharField(max_length=10, choices=TransactionStatus.choices, default=TransactionStatus.PENDING)

    idempotency_key = models.CharField(max_length=255)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'transaction'
        constraints = [
            models.UniqueConstraint(fields=['account', 'idempotency_key'], name='unique_idempotency_key_per_account')
        ]

    def __str__(self) -> str:
        return f'{self.type} {self.amount} on {self.account}'

