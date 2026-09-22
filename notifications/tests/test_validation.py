from django.test import SimpleTestCase

from notifications.services.validation import NotificationRowForm


class NotificationRowFormTests(SimpleTestCase):
    def test_valid_row_is_coerced(self) -> None:
        form = NotificationRowForm(
            {
                "external_id": "ext-1",
                "user_id": "42",
                "email": "user@example.com",
                "subject": "Тема",
                "message": "Текст",
            }
        )

        self.assertTrue(form.is_valid(), form.errors)
        self.assertEqual(form.cleaned_data["user_id"], 42)

    def test_invalid_row_reports_every_field(self) -> None:
        form = NotificationRowForm(
            {
                "external_id": "",
                "user_id": "abc",
                "email": "not-an-email",
                "subject": "Тема",
                "message": "",
            }
        )

        self.assertFalse(form.is_valid())
        self.assertEqual(
            set(form.errors), {"external_id", "user_id", "email", "message"}
        )
        text = form.error_text()
        for field in ("external_id", "user_id", "email", "message"):
            self.assertIn(f"{field}: ", text)
