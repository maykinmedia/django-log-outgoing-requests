from contextlib import contextmanager

from requests import RequestException, Session

from . import logger


def hook_requests_logging(response, *args, **kwargs):
    """
    A hook for requests library in order to add extra data to the logs
    """
    logger.debug(
        "Outgoing request",
        extra={
            "_is_log_outgoing_requests": True,
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
            "Outgoing request error",
            exc_info=exc,
            extra={"_is_log_outgoing_requests": True},
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
