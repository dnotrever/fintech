from datetime import date

from django.contrib.auth.base_user import AbstractBaseUser
from django.db.models import QuerySet

from account.models import Account, Transaction


def get_account_for_user(user: AbstractBaseUser) -> Account:
    return user.customer.account


def get_statement(*, account: Account, start_date: date, end_date: date) -> QuerySet[Transaction]:
    return Transaction.objects.filter(
        account=account,
        created_at__date__range=(start_date, end_date),
    ).order_by('-created_at')
