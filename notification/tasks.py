from celery import shared_task

from notification.services import send_email


@shared_task(bind=True, autoretry_for=(Exception,), retry_backoff=True, max_retries=3)
def send_email_task(self, *, to: str, subject: str, body: str) -> None:
    send_email(to=to, subject=subject, body=body)

