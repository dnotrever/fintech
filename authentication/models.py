import secrets
from datetime import timedelta

from django.conf import settings
from django.db import models
from django.utils import timezone

_TOKEN_LIFETIME = timedelta(hours=2)


def generate_token() -> str:
    return secrets.token_urlsafe(32)


class EmailConfirmationToken(models.Model):

    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='email_confirmation_tokens')
    token = models.CharField(max_length=64, unique=True, default=generate_token)
    created_at = models.DateTimeField(auto_now_add=True)
    confirmed_at = models.DateTimeField(null=True, blank=True)

    def is_expired(self) -> bool:
        return timezone.now() > self.created_at + _TOKEN_LIFETIME

