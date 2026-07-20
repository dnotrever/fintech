import random
import string
from typing import Callable

from django.db import IntegrityError, transaction

from account.models import Account, AccountStatus, AccountType
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
