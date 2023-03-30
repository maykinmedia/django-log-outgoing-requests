from django.apps import AppConfig


class LogOutgoingRequestsConfig(AppConfig):
    name = "log_outgoing_requests"

    def ready(self):
        from .log_requests import install_outgoing_requests_logging

        install_outgoing_requests_logging()
