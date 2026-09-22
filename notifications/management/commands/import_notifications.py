from pathlib import Path
from typing import Any
from zipfile import BadZipFile

from django.conf import settings
from django.core.management.base import BaseCommand, CommandError, CommandParser
from openpyxl.utils.exceptions import InvalidFileException

from notifications.services.importer import ImportReport, NotificationImporter
from notifications.services.sender import NotificationSender, SendReport
from notifications.services.xlsx_reader import XlsxFormatError, XlsxReader


class Command(BaseCommand):
    help = (
        "Импортирует письма из XLSX-файла и отправляет все письма, ожидающие отправки."
    )

    def add_arguments(self, parser: CommandParser) -> None:
        parser.add_argument("path", type=Path, help="Путь к XLSX-файлу.")
        parser.add_argument(
            "--batch-size",
            type=int,
            default=settings.NOTIFICATIONS_IMPORT_BATCH_SIZE,
            help="Сколько строк сохранять одним запросом (по умолчанию %(default)s).",
        )
        parser.add_argument(
            "--skip-send",
            action="store_true",
            help="Только импортировать, не отправлять письма.",
        )
        parser.add_argument(
            "--dry-run",
            action="store_true",
            help="Проверить файл и показать отчёт, ничего не сохраняя и не отправляя.",
        )

    def handle(self, *args: Any, **options: Any) -> None:
        path: Path = options["path"]
        batch_size: int = options["batch_size"]
        dry_run: bool = options["dry_run"]
        if batch_size < 1:
            raise CommandError("--batch-size должен быть положительным числом.")
        if not path.is_file():
            raise CommandError(f"Файл не найден: {path}")

        importer = NotificationImporter(batch_size=batch_size, dry_run=dry_run)
        try:
            report = importer.run(XlsxReader(path).iter_rows())
        except XlsxFormatError as exc:
            raise CommandError(str(exc)) from exc
        except (InvalidFileException, BadZipFile) as exc:
            raise CommandError(f"Файл не является XLSX: {path}") from exc
        self._print_import_report(path, report, dry_run=dry_run)

        if dry_run or options["skip_send"]:
            return
        send_report = NotificationSender(
            delay=settings.NOTIFICATIONS_SEND_DELAY
        ).send_pending()
        self._print_send_report(send_report)

    def _print_import_report(
        self, path: Path, report: ImportReport, *, dry_run: bool
    ) -> None:
        title = "Проверка файла завершена" if dry_run else "Импорт завершён"
        self.stdout.write(self.style.SUCCESS(f"{title}: {path}"))
        self.stdout.write(f"  обработано строк:   {report.processed}")
        self.stdout.write(f"  создано записей:    {report.created}")
        self.stdout.write(f"  пропущено записей:  {report.skipped}")
        self.stdout.write(f"  ошибочных строк:    {report.failed}")

    def _print_send_report(self, report: SendReport) -> None:
        self.stdout.write(self.style.SUCCESS("Отправка завершена"))
        self.stdout.write(f"  отправлено писем:   {report.sent}")
        self.stdout.write(f"  ошибок отправки:    {report.failed}")
