from datetime import date

from django.contrib.auth import get_user_model

from account.models import AccountType
from account.services import open_account
from customer.domain import CPF
from customer.models import Address, Customer

User = get_user_model()


def register_customer(
    *,
    username: str,
    email: str,
    password: str,
    cpf: str,
    phone: str,
    first_name: str,
    last_name: str,
    birth_date: date | None = None,
    address: dict,
) -> Customer:
    
    user = None
    customer = None

    try:
        user = User.objects.create_user(username=username, email=email, password=password)
        customer = Customer.objects.create(
            user=user,
            cpf=str(CPF(cpf)),
            phone=phone,
            first_name=first_name,
            last_name=last_name,
            birth_date=birth_date,
        )
        Address.objects.create(customer=customer, **address)
        open_account(customer=customer, account_type=AccountType.CHECKING)
    except Exception:
        if customer is not None:
            if hasattr(customer, 'account'):
                customer.account.delete()
            customer.delete()
        if user is not None:
            user.delete()
        raise
    
    return customer

