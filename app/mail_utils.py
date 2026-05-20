from __future__ import annotations

import logging
import os
import smtplib
from email.message import EmailMessage
from typing import Optional

logger = logging.getLogger(__name__)


def _smtp_config() -> dict:
    return {
        "host": os.environ.get("SMTP_HOST", "").strip(),
        "port": int(os.environ.get("SMTP_PORT", "587").strip() or "587"),
        "user": os.environ.get("SMTP_USER", "").strip(),
        "password": os.environ.get("SMTP_PASSWORD", "").strip(),
        "use_tls": (os.environ.get("SMTP_USE_TLS", "true").strip().lower() in {"1", "true", "yes", "y", "on"}),
        "from_email": os.environ.get("MAIL_FROM", "").strip(),
    }


def can_send_mail() -> bool:
    cfg = _smtp_config()
    return bool(cfg["host"] and cfg["from_email"] and (cfg["user"] or cfg["password"]))


def send_email(
    *,
    to_email: str,
    subject: str,
    body_text: str,
    body_html: Optional[str] = None,
) -> bool:
    """
    Отправляет письмо через SMTP.
    Никогда не падает наверх: при ошибках возвращает False и пишет лог.
    """
    cfg = _smtp_config()
    if not can_send_mail():
        logger.warning(
            "Mail is not configured. SMTP_HOST=%s MAIL_FROM=%s. Skipping send.",
            cfg["host"],
            cfg["from_email"],
        )
        return False

    msg = EmailMessage()
    msg["Subject"] = subject
    msg["From"] = cfg["from_email"]
    msg["To"] = to_email

    msg.set_content(body_text)

    if body_html:
        # EmailMessage поддерживает альтернативы
        msg.add_alternative(body_html, subtype="html")

    try:
        with smtplib.SMTP(cfg["host"], cfg["port"], timeout=20) as smtp:
            if cfg["use_tls"]:
                smtp.starttls()
            if cfg["user"]:
                smtp.login(cfg["user"], cfg["password"])
            smtp.send_message(msg)
        return True
    except Exception as e:
        logger.exception("Failed to send email to %s: %s", to_email, str(e))
        return False
