from unittest import mock

from django.test import SimpleTestCase, TestCase

from notifications.models import Notification, NotificationStatus
from notifications.services.sender import NotificationSender, SendReport


def make_notification(external_id: str, **fields: object) -> Notification:
    return Notification.objects.create(
        external_id=external_id,
        user_id=1,
        email="user@example.com",
        subject="Тема",
        message="Текст",
        **fields,
    )


class SendEmailTests(SimpleTestCase):
    def test_logs_notification_and_waits(self) -> None:
        notification = Notification(
            external_id="ext-1",
            user_id=7,
            email="user@example.com",
            subject="Привет",
            message="Текст",
        )

        with (
            mock.patch("notifications.services.sender.time.sleep") as sleep,
            self.assertLogs("notifications.services.sender", "INFO") as logs,
        ):
            NotificationSender(delay=0.25)._send_email(notification)

        self.assertIn("external_id=ext-1", logs.output[0])
        self.assertIn("user@example.com", logs.output[0])
        sleep.assert_called_once_with(0.25)


@mock.patch.object(NotificationSender, "_send_email")
class SendPendingTests(TestCase):
    def test_sends_only_pending_in_creation_order(self, send_email: mock.Mock) -> None:
        make_notification("sent", status=NotificationStatus.SENT)
        make_notification("b")
        make_notification("failed", status=NotificationStatus.FAILED)
        make_notification("a")

        report = NotificationSender(delay=0, chunk_size=1).send_pending()

        self.assertEqual(report, SendReport(sent=2))
        self.assertEqual(
            [call.args[0].external_id for call in send_email.call_args_list],
            ["b", "a"],
        )
        sent = Notification.objects.filter(status=NotificationStatus.SENT)
        self.assertEqual(sent.count(), 3)
        self.assertTrue(
            all(n.sent_at is not None for n in sent.filter(external_id__in="ab"))
        )
        self.assertFalse(Notification.objects.filter(status="pending").exists())

    def test_failure_marks_notification_failed(self, send_email: mock.Mock) -> None:
        make_notification("ok")
        make_notification("broken")
        send_email.side_effect = [None, RuntimeError("smtp down")]

        with self.assertLogs("notifications.services.sender", "ERROR"):
            report = NotificationSender(delay=0).send_pending()

        self.assertEqual(report, SendReport(sent=1, failed=1))
        broken = Notification.objects.get(external_id="broken")
        self.assertEqual(broken.status, NotificationStatus.FAILED)
        self.assertEqual(broken.last_error, "smtp down")
        self.assertIsNone(broken.sent_at)

    def test_nothing_to_send(self, send_email: mock.Mock) -> None:
        report = NotificationSender(delay=0).send_pending()

        self.assertEqual(report, SendReport())
        send_email.assert_not_called()
