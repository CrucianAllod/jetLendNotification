from django import forms


class NotificationRowForm(forms.Form):
    """Validate one file row and coerce values to model types."""

    external_id = forms.CharField(max_length=255)
    user_id = forms.IntegerField(min_value=1)
    email = forms.EmailField()
    subject = forms.CharField(max_length=255)
    message = forms.CharField()

    def error_text(self) -> str:
        """Format form errors as a single log line."""
        return "; ".join(
            f"{field}: {' '.join(str(message) for message in messages)}"
            for field, messages in self.errors.items()
        )
