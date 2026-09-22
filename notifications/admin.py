from typing import TYPE_CHECKING

from django.contrib import admin

from notifications.models import Notification

if TYPE_CHECKING:
    ModelAdminBase = admin.ModelAdmin[Notification]
else:
    ModelAdminBase = admin.ModelAdmin


@admin.register(Notification)
class NotificationAdmin(ModelAdminBase):
    list_display = ("external_id", "user_id", "email", "subject", "status", "sent_at")
    list_filter = ("status",)
    search_fields = ("external_id", "email", "subject")
    readonly_fields = ("created_at", "sent_at", "last_error")
    ordering = ("-created_at",)
