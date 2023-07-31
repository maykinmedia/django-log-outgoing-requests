import json
import logging

from django.utils import timezone

from requests import Session
from requests.exceptions import ConnectionError

logger = logging.getLogger("requests")


def hook_requests_logging(response, *args, **kwargs):
    """
    A hook for requests library in order to add extra data to the logs
    """
    extra = {"requested_at": timezone.now(), "req": response.request, "res": response}
    logger.debug("Outgoing request", extra=extra)


def hook_requests_exception(e, *args, **kwargs):
    extra = {
        "requested_at": timezone.now(),
        "exception": str(e),
        "method": kwargs.get("method", ""),
        "url": kwargs.get("url", ""),
        "req_body": str(kwargs.get("data", json.dumps(kwargs.get("json", {})))),
        "req_headers": kwargs.get("headers", {}),
    }
    logger.debug("Outgoing request exception", extra=extra)


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
        try:
            return self._lor_initial_request(*args, **kwargs)
        except ConnectionError as e:
            hook_requests_exception(e, *args, **kwargs)
            raise e

    Session.request = new_request
