import datetime as dt
import tempfile
from pathlib import Path

from django.test import SimpleTestCase

from notifications.services.xlsx_reader import RawRow, XlsxFormatError, XlsxReader
from notifications.tests.helpers import make_row, write_xlsx


class XlsxReaderTests(SimpleTestCase):
    def setUp(self) -> None:
        self._tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self._tmp.cleanup)
        self.path = Path(self._tmp.name) / "rows.xlsx"

    def test_reads_rows_with_excel_numbering(self) -> None:
        write_xlsx(self.path, [make_row("a"), make_row("b")])

        rows = list(XlsxReader(self.path).iter_rows())

        self.assertEqual(
            rows,
            [
                RawRow(2, {**self._values("a")}),
                RawRow(3, {**self._values("b")}),
            ],
        )

    def test_columns_are_matched_by_name_not_position(self) -> None:
        header = ("subject", "Email", " EXTERNAL_ID ", "comment", "message", "user_id")
        write_xlsx(
            self.path,
            [("Тема", "user@example.com", "ext-9", "лишнее", "Текст", 7)],
            header=header,
        )

        [row] = XlsxReader(self.path).iter_rows()

        self.assertEqual(
            row.values,
            {
                "external_id": "ext-9",
                "user_id": "7",
                "email": "user@example.com",
                "subject": "Тема",
                "message": "Текст",
            },
        )

    def test_missing_cells_and_empty_rows(self) -> None:
        write_xlsx(
            self.path,
            [
                ("ext-1",),
                (None, None, None, None, None),
                make_row("ext-2"),
            ],
        )

        rows = list(XlsxReader(self.path).iter_rows())

        self.assertEqual([row.number for row in rows], [2, 4])
        self.assertEqual(
            rows[0].values,
            {
                "external_id": "ext-1",
                "user_id": "",
                "email": "",
                "subject": "",
                "message": "",
            },
        )

    def test_cell_values_are_normalised_to_text(self) -> None:
        write_xlsx(
            self.path,
            [
                (
                    123.0,
                    4.5,
                    "  padded@example.com ",
                    dt.datetime(2026, 9, 22, 10, 30),
                    True,
                )
            ],
        )

        [row] = XlsxReader(self.path).iter_rows()

        self.assertEqual(
            row.values,
            {
                "external_id": "123",
                "user_id": "4.5",
                "email": "padded@example.com",
                "subject": "2026-09-22T10:30:00",
                "message": "True",
            },
        )

    def test_missing_required_column_raises(self) -> None:
        write_xlsx(self.path, [], header=("external_id", "user_id", "email"))

        with self.assertRaisesMessage(XlsxFormatError, "subject, message"):
            list(XlsxReader(self.path).iter_rows())

    def test_empty_sheet_raises(self) -> None:
        write_xlsx(self.path, [], header=None)

        with self.assertRaises(XlsxFormatError):
            list(XlsxReader(self.path).iter_rows())

    @staticmethod
    def _values(external_id: str) -> dict[str, str]:
        return {
            "external_id": external_id,
            "user_id": "1",
            "email": "user@example.com",
            "subject": "Тема",
            "message": "Текст письма",
        }
