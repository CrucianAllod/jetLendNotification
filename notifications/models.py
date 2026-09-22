from django.db import models


class NotificationStatus(models.TextChoices):
    PENDING = "pending", "Ожидает отправки"
    SENT = "sent", "Отправлено"
    FAILED = "failed", "Ошибка отправки"


class Notification(models.Model):
    """Email imported from an external system."""

    external_id = models.CharField(
        "внешний идентификатор",
        max_length=255,
        unique=True,
    )
    user_id = models.BigIntegerField("идентификатор пользователя")
    email = models.EmailField("email получателя")
    subject = models.CharField("тема письма", max_length=255)
    message = models.TextField("текст письма")
    status = models.CharField(
        "статус",
        max_length=16,
        choices=NotificationStatus.choices,
        default=NotificationStatus.PENDING,
        db_index=True,
    )
    last_error = models.TextField("последняя ошибка отправки", blank=True)
    created_at = models.DateTimeField("создано", auto_now_add=True)
    sent_at = models.DateTimeField("отправлено", null=True, blank=True)

    class Meta:
        verbose_name = "письмо"
        verbose_name_plural = "письма"
        ordering = ("pk",)

    def __str__(self) -> str:
        return f"{self.external_id} -> {self.email}"
