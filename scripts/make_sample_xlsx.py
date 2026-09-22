import argparse
from pathlib import Path

from openpyxl import Workbook

HEADER = ("external_id", "user_id", "email", "subject", "message")


Row = tuple[str | int, int | str, str, str, str]


def build_rows(count: int) -> list[Row]:
    rows: list[Row] = [
        (
            f"ext-{number}",
            number,
            f"user{number}@example.com",
            f"Уведомление №{number}",
            f"Здравствуйте! Это письмо №{number} из тестовой рассылки.",
        )
        for number in range(1, count + 1)
    ]
    rows.append(("ext-1", 1, "user1@example.com", "Дубликат", "Повтор ext-1"))
    rows.append(("ext-bad-email", 2, "не-email", "Ошибка", "Некорректный email"))
    rows.append(("", 3, "user3@example.com", "Ошибка", "Пустой external_id"))
    rows.append(("ext-bad-user", "abc", "user4@example.com", "Ошибка", "user_id"))
    return rows


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Генерирует XLSX-файл рассылки для локальной проверки импорта."
    )
    parser.add_argument("path", type=Path, help="куда сохранить файл")
    parser.add_argument(
        "--rows", type=int, default=20, help="количество корректных строк"
    )
    args = parser.parse_args()

    workbook = Workbook()
    sheet = workbook.active
    assert sheet is not None
    sheet.title = "notifications"
    sheet.append(HEADER)
    for row in build_rows(args.rows):
        sheet.append(row)
    args.path.parent.mkdir(parents=True, exist_ok=True)
    workbook.save(args.path)
    print(f"Файл сохранён: {args.path}")


if __name__ == "__main__":
    main()
