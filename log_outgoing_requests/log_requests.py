from contextlib import contextmanager

from requests import RequestException, Response, Session

from . import logger


def hook_requests_logging(response: Response, *args, **kwargs):
    """
    A hook for requests library in order to add extra data to the logs.
    """
    logger.debug(
        "outgoing_request_response_received",
        extra={
            "req": response.request,
            "res": response,
        },
    )


@contextmanager
def log_errors():
    try:
        yield
    except RequestException as exc:
        logger.debug(
            "outgoing_request_errored",
            exc_info=exc,
            extra={"request_exception": exc},
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
        if hook_requests_logging not in self.hooks["response"]:
            self.hooks["response"].append(hook_requests_logging)
        with log_errors():
            return self._lor_initial_request(*args, **kwargs)

    Session.request = new_request
