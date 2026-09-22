from django.test import TestCase

from notifications.models import Notification, NotificationStatus
from notifications.services.importer import ImportReport, NotificationImporter
from notifications.services.xlsx_reader import RawRow


def raw_row(number: int, external_id: str, **overrides: str) -> RawRow:
    values = {
        "external_id": external_id,
        "user_id": "1",
        "email": "user@example.com",
        "subject": "Тема",
        "message": "Текст",
    }
    values.update(overrides)
    return RawRow(number=number, values=values)


class NotificationImporterTests(TestCase):
    def test_creates_pending_notifications(self) -> None:
        report = NotificationImporter().run([raw_row(2, "a"), raw_row(3, "b")])

        self.assertEqual(report, ImportReport(processed=2, created=2))
        self.assertEqual(
            list(Notification.objects.values_list("external_id", "status")),
            [("a", NotificationStatus.PENDING), ("b", NotificationStatus.PENDING)],
        )

    def test_reimport_skips_existing_records(self) -> None:
        rows = [raw_row(2, "a"), raw_row(3, "b")]
        NotificationImporter().run(rows)

        report = NotificationImporter().run([*rows, raw_row(4, "c")])

        self.assertEqual(report, ImportReport(processed=3, created=1, skipped=2))
        self.assertEqual(Notification.objects.count(), 3)

    def test_duplicates_inside_file_are_skipped(self) -> None:
        report = NotificationImporter(batch_size=10).run(
            [raw_row(2, "a"), raw_row(3, "a", subject="Другая тема")]
        )

        self.assertEqual(report, ImportReport(processed=2, created=1, skipped=1))
        self.assertEqual(Notification.objects.get().subject, "Тема")

    def test_duplicates_across_batches_are_skipped(self) -> None:
        report = NotificationImporter(batch_size=1).run(
            [raw_row(2, "a"), raw_row(3, "a")]
        )

        self.assertEqual(report, ImportReport(processed=2, created=1, skipped=1))

    def test_invalid_rows_are_counted_and_logged(self) -> None:
        with self.assertLogs("notifications.services.importer", "WARNING") as logs:
            report = NotificationImporter().run(
                [raw_row(2, "a"), raw_row(3, "b", email="bad"), raw_row(4, "")]
            )

        self.assertEqual(report, ImportReport(processed=3, created=1, failed=2))
        self.assertEqual(len(logs.records), 2)
        self.assertIn("Строка 3", logs.output[0])
        self.assertIn("email", logs.output[0])
        self.assertIn("Строка 4", logs.output[1])

    def test_batches_use_constant_number_of_queries(self) -> None:
        rows = [raw_row(number, f"ext-{number}") for number in range(2, 12)]

        # 5 batches of 2 rows: SELECT of existing ids + INSERT per batch.
        with self.assertNumQueries(10):
            report = NotificationImporter(batch_size=2).run(rows)

        self.assertEqual(report, ImportReport(processed=10, created=10))

    def test_dry_run_does_not_write(self) -> None:
        NotificationImporter().run([raw_row(2, "a")])

        report = NotificationImporter(dry_run=True).run(
            [raw_row(2, "a"), raw_row(3, "b"), raw_row(4, "c", user_id="x")]
        )

        self.assertEqual(
            report, ImportReport(processed=3, created=1, skipped=1, failed=1)
        )
        self.assertEqual(Notification.objects.count(), 1)

    def test_rejects_non_positive_batch_size(self) -> None:
        with self.assertRaises(ValueError):
            NotificationImporter(batch_size=0)
