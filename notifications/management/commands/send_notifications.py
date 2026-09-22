from typing import Any

from django.conf import settings
from django.core.management.base import BaseCommand

from notifications.services.sender import NotificationSender


class Command(BaseCommand):
    help = "Отправляет все письма в статусе «ожидает отправки»."

    def handle(self, *args: Any, **options: Any) -> None:
        report = NotificationSender(
            delay=settings.NOTIFICATIONS_SEND_DELAY
        ).send_pending()
        self.stdout.write(self.style.SUCCESS("Отправка завершена"))
        self.stdout.write(f"  отправлено писем:   {report.sent}")
        self.stdout.write(f"  ошибок отправки:    {report.failed}")
