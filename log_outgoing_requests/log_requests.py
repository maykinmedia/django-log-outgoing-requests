import logging
from contextlib import contextmanager

from django.utils import timezone

from requests import RequestException, Session

logger = logging.getLogger("requests")


def hook_requests_logging(response, *args, **kwargs):
    """
    A hook for requests library in order to add extra data to the logs
    """
    extra = {"requested_at": timezone.now(), "req": response.request, "res": response}
    logger.debug("Outgoing request", extra=extra)


@contextmanager
def log_errors():
    timestamp = timezone.now()
    try:
        yield
    except RequestException as exc:
        logger.debug(
            "Outgoing request error",
            exc_info=exc,
            extra={"requested_at": timestamp, "req": exc.request, "res": exc.response},
        )
        raise


def install_outgoing_requests_logging():
    """
    Log all outgoing requests which are made by the library requests during a session.
    """

    if hasattr(Session, "_lor_initial_request"):
        logger.debug(
            "Session is already patched OR has an ``_lor_initial_request`` attribute."
        )
        return

    Session._lor_initial_request = Session.request  # type: ignore

    def new_request(self, *args, **kwargs):
        self.hooks["response"].append(hook_requests_logging)
        with log_errors():
            return self._lor_initial_request(*args, **kwargs)

    Session.request = new_request
