import logging

from django.utils import timezone

from requests import Session

logger = logging.getLogger("requests")


def hook_requests_logging(response, *args, **kwargs):
    """
    A hook for requests library in order to add extra data to the logs
    """
    extra = {"requested_at": timezone.now(), "req": response.request, "res": response}
    logger.debug("Outgoing request", extra=extra)


def install_outgoing_requests_logging():
    """
    Log all outgoing requests which are made by the library requests during a session.
    """

    if hasattr(Session, "_initial_request"):
        logger.debug(
            "Session is already patched OR has an ``_initial_request`` attribute."
        )
        return

    Session._initial_request = Session.request  # type: ignore

    def new_request(self, *args, **kwargs):
        self.hooks["response"].append(hook_requests_logging)
        return self._initial_request(*args, **kwargs)

    Session.request = new_request
