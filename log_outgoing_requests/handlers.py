"""
Provide robust and opinionated logging handlers.

`Log handlers <https://docs.python.org/3.12/library/logging.html#handler-objects>`_ are
responsible for sending the actual log records produced by loggers to their final
destination.

django-log-outgoing-requests provides a handler that knows how to send log records from
structlog to the database and save them into the
:class:`log_outgoing_requests.models.OutgoingRequestsLog` model.

Our handler implementations take care of packages/modules that rely on process-forking
behaviour, notably:

* uwsgi
* celery workers with prefork pool

Much of this implementation was taken from django-timeline-logger.
"""

# NOTE: Avoid import Django specifics at the module level to prevent circular imports.
# The handler is loaded eagerly at django startup when configuring settings.
from __future__ import annotations

import atexit
import logging
import os
import queue
import threading
import time
from collections.abc import Callable, Mapping
from datetime import timedelta
from logging.handlers import QueueHandler as _QueueHandler, QueueListener
from typing import TYPE_CHECKING, Any
from urllib.parse import urlparse

from django.db import close_old_connections
from django.utils import timezone
from django.utils.module_loading import import_string

from requests import PreparedRequest, RequestException, Response

from .compat import format_exception
from .conf import settings
from .typing import (
    AnyLogRecord,
    EventDict,
    is_any_request_log_record,
    is_error_request_log_record,
    is_request_log_record,
)

if TYPE_CHECKING:
    from .models import OutgoingRequestsLog

logger = logging.getLogger(__name__)


postfork: Callable[[Callable[..., Any]], Any]

# the uwsgi module is special - it's only available when the python code is loaded
# through uwsgi. With regular ``python`` usage, it does not exist.
try:  # pragma: no cover
    import uwsgi  # pyright: ignore[reportMissingModuleSource]
    from uwsgidecorators import postfork  # pyright: ignore[reportMissingModuleSource]
except ImportError:
    uwsgi = None
    postfork = lambda cb: None  # noqa: E731

_queue: queue.Queue = queue.Queue[EventDict](maxsize=0)
"""
Global queue singleton for the QueueHandler and QueueListener to communicate.

The queue is unbounded per the recommendations on an
`online article <https://runebook.dev/en/docs/python/library/logging.handlers/logging.handlers.QueueListener>`_.

TODO: it would probably be wise to monitor the queue size or when items get put on/taken
from the queue, e.g. with an OTel gauge instrument.
"""

_listener: QueueListener | None = None
"""
Queue listener singleton, ``None`` when it's not yet initialized.

Usually, the handler factory will result in the listener being initialized, but in
process-forking environments like uwsgi and celery workers, this is deferred until
after the process has forked. Failing to defer this results in deadlocks or other odd
behaviours.
"""

_lock = threading.Lock()
"""
Protect against race conditions between threads.

Trying to acquire a locked lock will block until it's unlocked (by another thread).

Note that Django's runserver runs in a subprocess, while typical production deployments
run multiple threads in one or more uwsgi/gunicorn processes.
"""


def get_listener() -> QueueListener | None:
    # Test helper to inspect the listener state.
    return _listener


def ensure_listener(*handlers: logging.Handler, _defer: bool) -> queue.Queue:
    """
    Ensure a listener thread is running for :class:`QueueHandler`.

    Creates a queue if it doesn't exist yet, and starts the background thread to
    listen to the queue to actually process the log records.

    We don't bother with preventing a background thread in the main runserver process
    that reloads the code and restarts the server - we don't expect any audit logs to
    be created there, and trying to detect these situations is too fragile compared
    to real uwsgi servers & management command situations. The idle background thread
    should not cause significant overhead.

    :arg _defer: Defer starting the background tread or not - by default on uwsgi we
      defer the startup and call te actual startup in te post fork hook.
    """
    global _listener, _queue

    def _ensure_listener(*args, **kwargs):
        return ensure_listener(*handlers, _defer=False)

    # we can't reliably use os.register_at_fork as it requires uwsgi's
    # py-call-uwsgi-fork-hooks flag, which can cause segfaults on Python 3.12:
    # https://github.com/unbit/uwsgi/issues/2738
    if _defer and uwsgi is not None:  # pragma: no cover
        postfork(_ensure_listener)

    # similar to uwsgi postfork, bind a handler when a celery worker process has
    # initialized
    try:  # pragma: no cover - no celery dependency available
        worker_process_init = import_string("celery.signals.worker_process_init")
        worker_process_init.connect(weak=False)(_ensure_listener)
    # Celery is an optional dependency
    except ImportError:
        pass

    # if a listener already exists, or if we must defer, short circuit and return the
    # queue already
    if _defer or _listener is not None:
        return _queue

    with _lock:
        _listener = QueueListener(_queue, *handlers, respect_handler_level=True)
        _listener.start()
        atexit.register(_stop_listener)
        return _queue


def _stop_listener():
    """
    Shut down (and drain) the listener thread/queue.
    """
    global _listener

    with _lock:
        if _listener is None:
            return
        try:
            _listener.stop()  # drains the queue before stopping
        finally:
            _listener = None


class QueueHandler(_QueueHandler):
    """
    Keep the raw log record.

    The stdlib implementation by default formats the log record to a string and clears
    most attributes to make them pickleable.
    """

    def prepare(self, record: logging.LogRecord):
        return record


def format_headers(headers: Mapping[str, str]):
    return "\n".join(f"{k}: {v}" for k, v in headers.items())


class DatabaseOutgoingRequestsHandler(logging.Handler):
    """
    Save the log record to the database if conditions are met.

    The handler checks if saving to the database is desired. If not, nothing happens.
    Next, request and response body are each checked if:

        * saving to database is desired
        * the content type is appropriate
        * the size of the body does not exceed the configured treshold

    If any of the conditions don't match, then the body is omitted.
    """

    buffer: list[OutgoingRequestsLog]

    def __init__(
        self,
        *,
        use_queue_mode: bool = False,
        buffer_size: int = 5,
        flush_interval: float = 3.0,
        **kwargs,
    ):
        super().__init__(**kwargs)

        # store configuration options
        self.use_queue_mode = use_queue_mode
        self.buffer_size = buffer_size if use_queue_mode else 1
        self.flush_interval = flush_interval

        # track internal buffer state
        self.buffer = []
        self._last_flush = time.monotonic()

    def emit(self, record: logging.LogRecord):
        try:
            self._emit_to_db(record)
        except Exception as exc:
            self.handleError(record)

            # XXX: should we add explicit transaction savepoint so we can recover when
            # running in the main thread?
            logger.error("log_saving_failed", exc_info=exc)
            if on_error := settings.LOG_OUTGOING_REQUESTS_HANDLER_ON_ERROR:
                on_error(exc)

    def _emit_to_db(self, record: AnyLogRecord) -> None:
        from .models import OutgoingRequestsLog, OutgoingRequestsLogConfig
        from .utils import process_body

        # skip requests not coming from the library requests
        if not record or not is_any_request_log_record(record):
            return

        self._maybe_close_old_connections()

        config = OutgoingRequestsLogConfig.get_solo()
        if not config.save_logs_enabled:
            return

        # check if we're dealing with success or error state
        response: Response | None
        exception: RequestException | None = None
        if is_request_log_record(record):
            # we have a response - this is the 'happy' flow (connectivity is okay)
            request = record.req
            response = record.res
        elif is_error_request_log_record(record):
            # we have an requests-specific exception
            exception = record.request_exception
            request = exception.request
            assert isinstance(request, PreparedRequest)
            response = exception.response  # likely None
        else:  # pragma: no cover
            logger.debug("Received log record that cannot be handled %r", record)
            return

        scrubbed_req_headers = request.headers.copy() if request else {}
        if "Authorization" in scrubbed_req_headers:
            scrubbed_req_headers["Authorization"] = "***hidden***"

        parsed_url = urlparse(request.url) if request else None

        # ensure we have a timezone aware timestamp. time.time() is platform dependent
        # about being UTC or a local time. A robust way is checking how many seconds ago
        # this record was created, and subtracting that from the current tz aware time.
        time_delta_logged_seconds = time.time() - record.created
        timestamp = timezone.now() - timedelta(seconds=time_delta_logged_seconds)

        kwargs = {
            "url": request.url if request else "(unknown)",
            "hostname": parsed_url.netloc if parsed_url else "(unknown)",
            "params": parsed_url.params if parsed_url else "(unknown)",
            "status_code": response.status_code if response is not None else None,
            "method": request.method if request else "(unknown)",
            "timestamp": timestamp,
            "response_ms": (
                int(response.elapsed.total_seconds() * 1000)
                if response is not None
                else 0
            ),
            "req_headers": format_headers(scrubbed_req_headers),
            "res_headers": format_headers(
                response.headers if response is not None else {}
            ),
            "trace": "\n".join(format_exception(exception)) if exception else "",
        }

        if config.save_body_enabled:
            # check request
            if (
                request
                and (
                    processed_request_body := process_body(request, config)
                ).allow_saving_to_db
            ):
                kwargs.update(
                    {
                        "req_content_type": processed_request_body.content_type,
                        "req_body": processed_request_body.content,
                        "req_body_encoding": processed_request_body.encoding,
                    }
                )

            # check response
            if (
                response is not None
                and (
                    processed_response_body := process_body(response, config)
                ).allow_saving_to_db
            ):
                kwargs.update(
                    {
                        "res_content_type": processed_response_body.content_type,
                        "res_body": processed_response_body.content,
                        "res_body_encoding": processed_response_body.encoding,
                    }
                )

        self.buffer.append(OutgoingRequestsLog(**kwargs))
        # check if we need to flush the buffer
        now = time.monotonic()
        if (
            len(self.buffer) >= self.buffer_size
            or (now - self._last_flush) > self.flush_interval
        ):
            self._flush()

    def _flush(self):
        """
        Flush the buffer to the database.
        """
        from .models import OutgoingRequestsLog

        OutgoingRequestsLog.objects.bulk_create(self.buffer)
        self.buffer = []
        self._last_flush = time.monotonic()
        self._maybe_close_old_connections()

    def _maybe_close_old_connections(self) -> None:
        # when running in a separate thread, clean up old connections. Because the
        # connection lives in its own thread, it doesn't get cleaned up by django's
        # 'request_finished' signal, so we must manually schedule the cleanup. Django
        # will re-open the connection when queries are made.
        if self.use_queue_mode:
            close_old_connections()

    def close(self):
        try:
            self._flush()
        finally:
            self._maybe_close_old_connections()
            super().close()


def outgoing_requests_handler_factory(
    *, buffer_size: int = 5, flush_interval: float = 3.0
) -> QueueHandler | DatabaseOutgoingRequestsHandler:
    """
    Create a logging handler instance suitable for production or testing.

    By default, a queue-based handler is configured so that the actual logging of
    outgoing requests can be offloaded to a worker thread. This improves performance by
    taking database queries out of the main thread, and improves log integrity because
    the log insertions run in a separate thread and associated database transaction.

    However, in (unit) test setups, you want to force the logs to be written in the same
    test transaction so that at the end of the test, the log record creation is rolled
    back by the test transaction, otherwise you break test isolation substantially
    and/or slow down test suites considerably by forcing them to be
    :class:`django.test.TransactionTestCase`.

    The appropriate handler is selected based on the
    ``LOG_OUTGOING_REQUESTS_HANDLER_USE_QUEUE`` Django setting.

    Note that you cannot change this setup at runtime in tests through
    :func:`django.test.override_settings`, as the logging config does not get
    reinitialized when settings change (as it should be!). You should configure CI/local
    test environments to apply conditional configurations.

    :arg buffer_size: Maximum size for the internal buffer. Passed along to the
      :class:`DatabaseOutgoingRequestsHandler` initializer.
    :arg flush_interval: Maximum age between database writes. Passed along to the
      :class:`DatabaseOutgoingRequestsHandler` initializer.
    """
    use_queue: bool = settings.LOG_OUTGOING_REQUESTS_HANDLER_USE_QUEUE
    db_logger_handler = DatabaseOutgoingRequestsHandler(
        use_queue_mode=use_queue,
        buffer_size=buffer_size,
        flush_interval=flush_interval,
    )

    # if the project does not opt out of the queue, return the handler as-is which will
    # run in the main thread
    if not use_queue:
        return db_logger_handler

    # otherwise set up the queue system. First, check if we explicitly opt-out of
    # deferred queue listener start.
    _defer: bool
    # Using an environment variable is the most robust way to defer in celery workers.
    match os.environ.get("_LOG_OUTGOING_REQUESTS_LOGGER_DEFER_LISTENER", "").lower():
        case "false" | "0":
            _defer = False
        case "true" | "1":
            _defer = True
        case _:  # pragma: no cover
            _defer = uwsgi is not None

    queue = ensure_listener(db_logger_handler, _defer=_defer)
    return QueueHandler(queue=queue)
