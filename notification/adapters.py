import resend
from django.conf import settings
from resend.http_client_requests import RequestsClient

_TIMEOUT_SECONDS = 10


class ResendEmailAdapter:
    
    def __init__(self) -> None:
        resend.default_http_client = RequestsClient(timeout=_TIMEOUT_SECONDS)

    def send(self, *, to: str, subject: str, body: str) -> None:
        resend.api_key = settings.RESEND_API_KEY
        resend.Emails.send({
            'from': settings.DEFAULT_FROM_EMAIL,
            'to': [to],
            'subject': subject,
            'html': body,
        })

