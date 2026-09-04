import logging
import sys

from pythonjsonlogger import jsonlogger

from app.core.config import get_settings

SENSITIVE_KEYS = {"password", "token", "secret", "authorization", "refresh_token", "access_token"}


def redact(record: dict) -> dict:
    for key in list(record.keys()):
        if any(s in key.lower() for s in SENSITIVE_KEYS):
            record[key] = "***REDACTED***"
    return record


class RedactingJsonFormatter(jsonlogger.JsonFormatter):
    def process_log_record(self, log_record):
        return redact(super().process_log_record(log_record))


def configure_logging() -> None:
    settings = get_settings()
    handler = logging.StreamHandler(sys.stdout)
    handler.setFormatter(
        RedactingJsonFormatter(
            "%(asctime)s %(levelname)s %(name)s %(message)s %(request_id)s",
            rename_fields={"asctime": "timestamp", "levelname": "level"},
            defaults={"request_id": "-"},
        )
    )
    root = logging.getLogger()
    root.handlers = [handler]
    root.setLevel(settings.log_level)
