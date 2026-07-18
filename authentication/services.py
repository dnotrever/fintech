import logging

from django.conf import settings

from authentication.models import EmailConfirmationToken
from notification.services import send_email

logger = logging.getLogger(__name__)


def send_confirmation_email(user) -> None:
    EmailConfirmationToken.objects.filter(user=user, confirmed_at__isnull=True).delete()
    confirmation = EmailConfirmationToken.objects.create(user=user)
    confirmation_url = f'{settings.BACKEND_BASE_URL}/auth/confirm/{confirmation.token}/'
    try:
        send_email(
            to=user.email,
            subject='Confirme seu cadastro',
            body=f'Clique para confirmar seu cadastro: {confirmation_url}',
        )
    except Exception:
        logger.exception('Failed to send confirmation email to user_id=%s', user.id)

