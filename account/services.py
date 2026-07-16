import random
import string

from django.contrib.auth.base_user import AbstractBaseUser
from django.db import IntegrityError, transaction

from account.models import Account, AccountType

_ACCOUNT_NUMBER_LENGTH = 6
_MAX_GENERATION_ATTEMPTS = 5


class AccountNumberGenerationError(Exception):
    pass


def _generate_account_number() -> str:
    return ''.join(random.choices(string.digits, k=_ACCOUNT_NUMBER_LENGTH))


def create_account(*, owner: AbstractBaseUser, agency: str, account_type: str = AccountType.CHECKING) -> Account:
    for _ in range(_MAX_GENERATION_ATTEMPTS):
        try:
            with transaction.atomic():
                return Account.objects.create(
                    owner=owner,
                    agency=agency,
                    account_type=account_type,
                    account_number=_generate_account_number(),
                )
        except IntegrityError:
            continue

    raise AccountNumberGenerationError('Could not generate a unique account number.')

