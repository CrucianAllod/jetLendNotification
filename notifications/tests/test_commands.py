import tempfile
from io import StringIO
from pathlib import Path
from unittest import mock

from django.core.management import CommandError, call_command
from django.test import TestCase, override_settings

from notifications.models import Notification, NotificationStatus
from notifications.services.sender import NotificationSender
from notifications.tests.helpers import make_row, write_xlsx


@override_settings(NOTIFICATIONS_SEND_DELAY=0)
class ImportNotificationsCommandTests(TestCase):
    def setUp(self) -> None:
        self._tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self._tmp.cleanup)
        self.path = Path(self._tmp.name) / "notifications.xlsx"

    def run_command(self, *args: object) -> str:
        stdout = StringIO()
        call_command("import_notifications", *args, stdout=stdout)
        return stdout.getvalue()

    def test_imports_and_sends(self) -> None:
        write_xlsx(
            self.path,
            [make_row("a"), make_row("b"), make_row("a"), make_row("c", email="bad")],
        )

        with self.assertLogs("notifications.services.sender", "INFO") as logs:
            output = self.run_command(self.path)

        self.assertIn("обработано строк:   4", output)
        self.assertIn("создано записей:    2", output)
        self.assertIn("пропущено записей:  1", output)
        self.assertIn("ошибочных строк:    1", output)
        self.assertIn("отправлено писем:   2", output)
        self.assertIn("ошибок отправки:    0", output)
        self.assertEqual(len(logs.records), 2)
        self.assertEqual(
            Notification.objects.filter(status=NotificationStatus.SENT).count(), 2
        )

    def test_reimport_does_not_resend(self) -> None:
        write_xlsx(self.path, [make_row("a")])
        self.run_command(self.path)

        with mock.patch.object(NotificationSender, "_send_email") as send_email:
            output = self.run_command(self.path)

        self.assertIn("пропущено записей:  1", output)
        self.assertIn("отправлено писем:   0", output)
        send_email.assert_not_called()

    def test_skip_send_leaves_notifications_pending(self) -> None:
        write_xlsx(self.path, [make_row("a")])

        output = self.run_command(self.path, "--skip-send")

        self.assertNotIn("Отправка", output)
        self.assertEqual(Notification.objects.get().status, NotificationStatus.PENDING)

    def test_dry_run_changes_nothing(self) -> None:
        write_xlsx(self.path, [make_row("a")])

        output = self.run_command(self.path, "--dry-run")

        self.assertIn("Проверка файла завершена", output)
        self.assertIn("создано записей:    1", output)
        self.assertFalse(Notification.objects.exists())

    def test_batch_size_is_passed_to_importer(self) -> None:
        write_xlsx(self.path, [make_row("a"), make_row("b"), make_row("c")])

        # 2 batches (SELECT + INSERT each), then SELECT of the queue and 3 UPDATEs.
        with self.assertNumQueries(8):
            self.run_command(self.path, "--batch-size", "2")

    def test_missing_file(self) -> None:
        with self.assertRaisesMessage(CommandError, "Файл не найден"):
            self.run_command(self.path)

    def test_not_an_xlsx(self) -> None:
        self.path.write_text("external_id,user_id\n")

        with self.assertRaisesMessage(CommandError, "не является XLSX"):
            self.run_command(self.path)

    def test_missing_columns(self) -> None:
        write_xlsx(self.path, [], header=("external_id",))

        with self.assertRaisesMessage(CommandError, "обязательные колонки"):
            self.run_command(self.path)

    def test_invalid_batch_size(self) -> None:
        write_xlsx(self.path, [])

        with self.assertRaisesMessage(CommandError, "--batch-size"):
            self.run_command(self.path, "--batch-size", "0")


@override_settings(NOTIFICATIONS_SEND_DELAY=0)
class SendNotificationsCommandTests(TestCase):
    def test_sends_pending(self) -> None:
        Notification.objects.create(
            external_id="a",
            user_id=1,
            email="user@example.com",
            subject="Тема",
            message="Текст",
        )
        stdout = StringIO()

        with self.assertLogs("notifications.services.sender", "INFO"):
            call_command("send_notifications", stdout=stdout)

        self.assertIn("отправлено писем:   1", stdout.getvalue())
        self.assertEqual(Notification.objects.get().status, NotificationStatus.SENT)
