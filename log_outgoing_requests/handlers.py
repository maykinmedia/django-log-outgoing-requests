# NOTE: Avoid import Django specifics at the module level to prevent circular imports.
# The handler is loaded eagerly at django startup when configuring settings.
import logging
import time
from contextlib import contextmanager
from datetime import timedelta
from typing import Optional, cast
from urllib.parse import urlparse

from django.utils import timezone

from requests import PreparedRequest, RequestException, Response

from .compat import format_exception
from .typing import (
    AnyLogRecord,
    ErrorRequestLogRecord,
    RequestLogRecord,
    is_request_log_record,
)

logger = logging.getLogger(__name__)


@contextmanager
def supress_errors():
    try:
        yield
    except Exception as exc:
        logger.error("Could not persist log record to DB", exc_info=exc)


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

    @supress_errors()
    def emit(self, record: AnyLogRecord):
        from .models import OutgoingRequestsLog, OutgoingRequestsLogConfig
        from .utils import process_body

        # skip requests not coming from the library requests
        if not record or not is_request_log_record(record):
            return

        config = OutgoingRequestsLogConfig.get_solo()
        assert isinstance(config, OutgoingRequestsLogConfig)
        if not config.save_logs_enabled:
            return

        # Python 3.10 TypeGuard can be useful here
        record = cast(RequestLogRecord, record)

        # check if we're dealing with success or error state
        exception = record.exc_info[1] if record.exc_info else None
        if (response := getattr(record, "res", None)) is not None:
            # we have a response - this is the 'happy' flow (connectivity is okay)
            record = cast(RequestLogRecord, record)
            request = record.req
        elif isinstance(exception, RequestException):
            record = cast(ErrorRequestLogRecord, record)
            # we have an requests-specific exception
            request: Optional[PreparedRequest] = exception.request
            response: Optional[Response] = exception.response  # likely None
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
            "status_code": response.status_code if response else None,
            "method": request.method if request else "(unknown)",
            "timestamp": timestamp,
            "response_ms": int(response.elapsed.total_seconds() * 1000)
            if response
            else 0,
            "req_headers": self.format_headers(scrubbed_req_headers),
            "res_headers": self.format_headers(response.headers if response else {}),
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
                response
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

        OutgoingRequestsLog.objects.create(**kwargs)

    def format_headers(self, headers):
        return "\n".join(f"{k}: {v}" for k, v in headers.items())
