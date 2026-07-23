import random
import string
from decimal import Decimal
from typing import Callable

from django.db import IntegrityError, transaction

from account.models import Account, AccountStatus, AccountType, Transaction, TransactionStatus, TransactionType
from customer.models import Customer

_ACCOUNT_NUMBER_LENGTH = 6
_MAX_GENERATION_ATTEMPTS = 5
_DEFAULT_AGENCY = '00001'


def _generate_account_number() -> str:
    return ''.join(random.choices(string.digits, k=_ACCOUNT_NUMBER_LENGTH))


def open_account(
    *,
    customer: Customer,
    account_type: str = AccountType.CHECKING,
    status: str = AccountStatus.ACTIVE,
    number_generator: Callable[[], str] = _generate_account_number,
) -> Account:
    for _ in range(_MAX_GENERATION_ATTEMPTS):
        try:
            with transaction.atomic():
                return Account.objects.create(
                    customer=customer,
                    agency=_DEFAULT_AGENCY,
                    account_type=account_type,
                    status=status,
                    account_number=number_generator(),
                )
        except IntegrityError:
            continue
    raise AccountNumberGenerationError('Could not generate a unique account number.')


class AccountNumberGenerationError(Exception):
    pass


def deposit(
    *,
    account: Account,
    amount: Decimal,
    idempotency_key: str
) -> Transaction:
    existing = Transaction.objects.filter(account=account, idempotency_key=idempotency_key).first()
    if existing is not None:
        if existing.amount != amount:
            raise IdempotencyKeyConflictError(f'Idempotency key {idempotency_key} was already used with a different amount.')
        return existing
    try:
        with transaction.atomic():
            account.credit(amount)
            account.save(update_fields=['balance', 'updated_at'])
            return Transaction.objects.create(
                account=account,
                type=TransactionType.DEPOSIT,
                amount=amount,
                balance_after=account.balance,
                status=TransactionStatus.COMPLETED,
                idempotency_key=idempotency_key,
            )
    except IntegrityError:
        return Transaction.objects.get(account=account, idempotency_key=idempotency_key)


class IdempotencyKeyConflictError(Exception):
    pass

