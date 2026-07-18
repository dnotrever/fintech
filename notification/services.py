from notification.adapters import ResendEmailAdapter
from notification.channels import EmailChannel

_default_channel = ResendEmailAdapter()


def send_email(*, to: str, subject: str, body: str, channel: EmailChannel | None = None) -> None:
    (channel or _default_channel).send(to=to, subject=subject, body=body)
