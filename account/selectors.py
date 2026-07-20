from django.contrib.auth.base_user import AbstractBaseUser

from account.models import Account


def get_account_for_user(user: AbstractBaseUser) -> Account:
    return user.customer.account
