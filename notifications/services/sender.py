import logging
import time
from dataclasses import dataclass

from django.utils import timezone

from notifications.models import Notification, NotificationStatus

logger = logging.getLogger(__name__)


@dataclass(slots=True)
class SendReport:
    """Send totals."""

    sent: int = 0
    failed: int = 0


class NotificationSender:
    """Send pending notifications one by one, persisting status after each."""

    def __init__(self, *, delay: float, chunk_size: int = 500) -> None:
        self._delay = delay
        self._chunk_size = chunk_size

    def send_pending(self) -> SendReport:
        report = SendReport()
        pending = Notification.objects.filter(
            status=NotificationStatus.PENDING
        ).order_by("pk")
        for notification in pending.iterator(chunk_size=self._chunk_size):
            self._send_one(notification, report)
        return report

    def _send_one(self, notification: Notification, report: SendReport) -> None:
        try:
            self._send_email(notification)
        except Exception as exc:
            # One failed email must not stop the whole queue.
            report.failed += 1
            logger.exception(
                "Не удалось отправить письмо external_id=%s", notification.external_id
            )
            notification.status = NotificationStatus.FAILED
            notification.last_error = str(exc)
        else:
            report.sent += 1
            notification.status = NotificationStatus.SENT
            notification.sent_at = timezone.now()
            notification.last_error = ""
        notification.save(update_fields=["status", "sent_at", "last_error"])

    def _send_email(self, notification: Notification) -> None:
        """Fake send: log the email and sleep for the configured delay."""
        logger.info(
            "Письмо external_id=%s user_id=%s email=%s subject=%r",
            notification.external_id,
            notification.user_id,
            notification.email,
            notification.subject,
        )
        time.sleep(self._delay)
