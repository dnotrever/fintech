import resend
from django.conf import settings


class ResendEmailAdapter:
    def send(self, *, to: str, subject: str, body: str) -> None:
        resend.api_key = settings.RESEND_API_KEY
        resend.Emails.send({
            'from': settings.DEFAULT_FROM_EMAIL,
            'to': [to],
            'subject': subject,
            'html': body,
        })
