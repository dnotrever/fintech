from django.conf import settings
from django.db import transaction

from authentication.models import EmailConfirmationToken
from notification.tasks import send_email_task


def send_confirmation_email(user) -> None:
    EmailConfirmationToken.objects.filter(user=user, confirmed_at__isnull=True).delete()
    confirmation = EmailConfirmationToken.objects.create(user=user)
    confirmation_url = f'{settings.FRONTEND_BASE_URL}/auth/confirm/{confirmation.token}/'
    transaction.on_commit(
        lambda: send_email_task.delay(
            to=user.email,
            subject='Confirme seu cadastro',
            body=f'Clique para confirmar seu cadastro: {confirmation_url}',
        )
    )

