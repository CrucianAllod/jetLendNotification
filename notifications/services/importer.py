import logging
from collections.abc import Iterable
from dataclasses import dataclass
from itertools import batched

from notifications.models import Notification
from notifications.services.validation import NotificationRowForm
from notifications.services.xlsx_reader import RawRow

logger = logging.getLogger(__name__)


@dataclass(slots=True)
class ImportReport:
    """Import totals; ``processed == created + skipped + failed``."""

    processed: int = 0
    created: int = 0
    skipped: int = 0
    failed: int = 0


class NotificationImporter:
    """Create notifications from file rows in batches, skipping known ``external_id``."""

    def __init__(self, *, batch_size: int = 1000, dry_run: bool = False) -> None:
        if batch_size < 1:
            raise ValueError("batch_size должен быть положительным числом.")
        self._batch_size = batch_size
        self._dry_run = dry_run

    def run(self, rows: Iterable[RawRow]) -> ImportReport:
        report = ImportReport()
        for batch in batched(rows, self._batch_size):
            self._import_batch(batch, report)
        return report

    def _import_batch(self, batch: tuple[RawRow, ...], report: ImportReport) -> None:
        candidates: dict[str, Notification] = {}
        for row in batch:
            report.processed += 1
            form = NotificationRowForm(row.values)
            if not form.is_valid():
                report.failed += 1
                logger.warning(
                    "Строка %d не импортирована: %s", row.number, form.error_text()
                )
                continue
            external_id: str = form.cleaned_data["external_id"]
            if external_id in candidates:
                report.skipped += 1
                logger.info(
                    "Строка %d пропущена: external_id=%s уже встречался в файле",
                    row.number,
                    external_id,
                )
                continue
            candidates[external_id] = Notification(**form.cleaned_data)

        if not candidates:
            return
        existing = set(
            Notification.objects.filter(external_id__in=candidates).values_list(
                "external_id", flat=True
            )
        )
        new_notifications = [
            notification
            for external_id, notification in candidates.items()
            if external_id not in existing
        ]
        report.skipped += len(existing)
        if existing:
            logger.info("Пропущено %d записей, уже существующих в базе", len(existing))
        if not self._dry_run:
            Notification.objects.bulk_create(new_notifications, ignore_conflicts=True)
        report.created += len(new_notifications)
