from email.message import EmailMessage
import smtplib

from src.common.config import Settings


def send_email(settings: Settings, to_address: str, subject: str, body: str) -> None:
    if not settings.smtp_host:
        raise ValueError("SMTP_HOST is not configured.")
    if not settings.smtp_from:
        raise ValueError("SMTP_FROM is not configured.")

    message = EmailMessage()
    message["From"] = settings.smtp_from
    message["To"] = to_address
    message["Subject"] = subject
    message.set_content(body)

    with smtplib.SMTP(settings.smtp_host, settings.smtp_port, timeout=20) as server:
        if settings.smtp_use_tls:
            server.starttls()
        if settings.smtp_user and settings.smtp_password:
            server.login(settings.smtp_user, settings.smtp_password)
        server.send_message(message)
