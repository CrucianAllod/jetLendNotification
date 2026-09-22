from collections.abc import Sequence
from pathlib import Path
from typing import Any

from openpyxl import Workbook

DEFAULT_HEADER: tuple[str, ...] = (
    "external_id",
    "user_id",
    "email",
    "subject",
    "message",
)


def make_row(
    external_id: str = "ext-1",
    user_id: Any = 1,
    email: str = "user@example.com",
    subject: str = "Тема",
    message: str = "Текст письма",
) -> tuple[Any, ...]:
    """Build a data row in ``DEFAULT_HEADER`` order."""
    return (external_id, user_id, email, subject, message)


def write_xlsx(
    path: Path,
    rows: Sequence[Sequence[Any]],
    header: Sequence[Any] | None = DEFAULT_HEADER,
) -> Path:
    """Write a single-sheet XLSX with an optional header and data rows."""
    workbook = Workbook()
    sheet = workbook.active
    assert sheet is not None
    if header is not None:
        sheet.append(list(header))
    for row in rows:
        sheet.append(list(row))
    workbook.save(path)
    return path
