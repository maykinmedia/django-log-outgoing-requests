from django.apps import AppConfig
from django.utils.translation import gettext_lazy as _


class LogOutgoingRequestsConfig(AppConfig):
    name = "log_outgoing_requests"
    verbose_name = _("Outgoing request logs")
    default_auto_field = "django.db.models.BigAutoField"

    def ready(self):
        from .log_requests import install_outgoing_requests_logging

        install_outgoing_requests_logging()
