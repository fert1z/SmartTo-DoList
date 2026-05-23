from __future__ import annotations

import logging
import os
import smtplib
import ssl
from email.message import EmailMessage
from typing import Optional

logger = logging.getLogger(__name__)


def _smtp_config() -> dict:
    """
    Unified SMTP configuration from environment variables.
    Supports both MAIL_* and SMTP_* prefixes for backwards compatibility.
    """
    # Try MAIL_* first, fall back to SMTP_* for backwards compatibility
    host = os.environ.get("MAIL_SERVER") or os.environ.get("SMTP_HOST", "").strip()
    port_str = os.environ.get("MAIL_PORT") or os.environ.get("SMTP_PORT", "587")
    user = os.environ.get("MAIL_USERNAME") or os.environ.get("SMTP_USER", "").strip()
    password = os.environ.get("MAIL_PASSWORD") or os.environ.get("SMTP_PASSWORD", "").strip()
    from_email = os.environ.get("MAIL_DEFAULT_SENDER") or os.environ.get("MAIL_FROM", "").strip()
    use_tls_str = os.environ.get("MAIL_USE_TLS", "1").strip().lower()
    require_auth_str = os.environ.get("MAIL_REQUIRE_AUTH", "1").strip().lower()
    
    # Default to TLS if MAIL_USE_TLS is not set or is "1"
    use_tls = use_tls_str in {"1", "true", "yes", "y", "on"}
    require_auth = require_auth_str in {"1", "true", "yes", "y", "on"}
    
    try:
        port = int(port_str or 587)
    except ValueError:
        logger.warning('Invalid MAIL_PORT/SMTP_PORT value: %s. Falling back to 587.', port_str)
        port = 587
    
    return {
        "host": host.strip() if isinstance(host, str) else "",
        "port": port,
        "user": user,
        "password": password,
        "use_tls": use_tls,
        "from_email": from_email,
        "require_auth": require_auth,
    }


def can_send_mail() -> bool:
    cfg = _smtp_config()
    if not (cfg["host"] and cfg["from_email"]):
        return False
    if cfg["require_auth"] and not (cfg["user"] and cfg["password"]):
        logger.warning(
            'Mail authorization required but MAIL_USERNAME or MAIL_PASSWORD is missing. '
            'Set MAIL_REQUIRE_AUTH=0 to allow anonymous SMTP if you understand the risk.'
        )
        return False
    return True


def send_email(
    *,
    to_email: str,
    subject: str,
    body_text: str,
    body_html: Optional[str] = None,
) -> bool:
    """
    Sends email via SMTP.
    Supports both TLS (port 587) and SMTPS (port 465).
    Never raises exceptions — returns False on error and logs the issue.
    """
    cfg = _smtp_config()
    if not can_send_mail():
        logger.warning(
            "Mail is not configured. MAIL_SERVER=%s MAIL_DEFAULT_SENDER=%s. Skipping send.",
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
        msg.add_alternative(body_html, subtype="html")

    try:
        port = cfg["port"]
        host = cfg["host"]
        use_tls = cfg["use_tls"]
        
        # Detect SMTPS (implicit TLS on port 465) vs SMTP with STARTTLS (port 587)
        if port == 465 and not use_tls:
            # Use SMTPS (implicit TLS)
            context = ssl.create_default_context()
            with smtplib.SMTP_SSL(host, port, timeout=20, context=context) as smtp:
                if cfg["user"]:
                    smtp.login(cfg["user"], cfg["password"])
                smtp.send_message(msg)
        else:
            # Use SMTP with optional STARTTLS
            with smtplib.SMTP(host, port, timeout=20) as smtp:
                if use_tls:
                    context = ssl.create_default_context()
                    smtp.starttls(context=context)
                if cfg["user"]:
                    smtp.login(cfg["user"], cfg["password"])
                smtp.send_message(msg)
        
        return True
    except Exception as e:
        logger.exception("Failed to send email to %s: %s", to_email, str(e))
        return False
