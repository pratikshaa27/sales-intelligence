import logging

from app.core.config import get_settings

logger = logging.getLogger(__name__)
settings = get_settings()


async def send_email(*, to: str, subject: str, body: str) -> None:
    """Send a transactional email.

    No SMTP credentials are configured for local/dev by default (see .env.example), so this
    logs the notification instead of silently pretending delivery happened. Wire a real SMTP
    or provider client here once SMTP_* settings are populated for a given environment.
    """
    if not settings.smtp_host:
        logger.info(
            "email_not_sent_no_smtp_configured",
            extra={"to": to, "subject": subject},
        )
        return

    raise NotImplementedError("SMTP delivery is not implemented yet; configure a provider client.")
