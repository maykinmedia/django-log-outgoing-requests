# NOTE: Avoid import Django specifics at the module level to prevent circular imports.
# The handler is loaded eagerly at django startup when configuring settings.
import logging
import traceback
from datetime import datetime
from logging import LogRecord
from typing import Union, cast
from urllib.parse import urlparse

from requests.models import PreparedRequest, Response

logger = logging.getLogger(__name__)


class RequestLogRecord(LogRecord):
    requested_at: datetime
    req: PreparedRequest
    res: Response


AnyLogRecord = Union[LogRecord, RequestLogRecord]


def is_request_log_record(record: AnyLogRecord) -> bool:
    attrs = ("requested_at", "req", "res")
    if any(not hasattr(record, attr) for attr in attrs):
        return False
    return True


def is_exception_log_record(record: AnyLogRecord) -> bool:
    attrs = ("requested_at", "exception", "method", "url", "req_headers")
    if any(not hasattr(record, attr) for attr in attrs):
        return False
    return True


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

    def log_request(self, record, config):
        from .models import OutgoingRequestsLog
        from .utils import process_body

        # Typescript type predicates would be cool here :)
        record = cast(RequestLogRecord, record)

        scrubbed_req_headers = record.req.headers.copy()

        if "Authorization" in scrubbed_req_headers:
            scrubbed_req_headers["Authorization"] = "***hidden***"

        trace = traceback.format_exc() if record.exc_info else ""

        parsed_url = urlparse(record.req.url)
        kwargs = {
            "url": record.req.url,
            "hostname": parsed_url.netloc,
            "params": parsed_url.params,
            "status_code": record.res.status_code,
            "method": record.req.method,
            "timestamp": record.requested_at,
            "response_ms": int(record.res.elapsed.total_seconds() * 1000),
            "req_headers": self.format_headers(scrubbed_req_headers),
            "res_headers": self.format_headers(record.res.headers),
            "trace": trace,
        }

        if config.save_body_enabled:
            # check request
            processed_request_body = process_body(record.req, config)
            if processed_request_body.allow_saving_to_db:
                kwargs.update(
                    {
                        "req_content_type": processed_request_body.content_type,
                        "req_body": processed_request_body.content,
                        "req_body_encoding": processed_request_body.encoding,
                    }
                )

            # check response
            processed_response_body = process_body(record.res, config)
            if processed_response_body.allow_saving_to_db:
                kwargs.update(
                    {
                        "res_content_type": processed_response_body.content_type,
                        "res_body": processed_response_body.content,
                        "res_body_encoding": processed_response_body.encoding,
                    }
                )

        OutgoingRequestsLog.objects.create(**kwargs)

    def log_exception(self, record, config):
        from django.db import transaction

        from .models import OutgoingRequestsLog
        from .utils import process_body

        scrubbed_req_headers = record.req_headers.copy()

        if "Authorization" in scrubbed_req_headers:
            scrubbed_req_headers["Authorization"] = "***hidden***"

        parsed_url = urlparse(record.url)

        kwargs = {
            "url": record.url,
            "hostname": parsed_url.netloc,
            "params": parsed_url.params,
            "method": record.method,
            "timestamp": record.requested_at,
            "trace": record.exception,
            "req_headers": self.format_headers(scrubbed_req_headers),
        }

        try:
            with transaction.atomic():
                OutgoingRequestsLog.objects.create(**kwargs)
        except Exception as e:
            logger.exception(e)

    def emit(self, record: AnyLogRecord):
        from .models import OutgoingRequestsLogConfig

        config = cast(OutgoingRequestsLogConfig, OutgoingRequestsLogConfig.get_solo())
        if not config.save_logs_enabled:
            return

        # skip requests not coming from the library requests
        if record and is_request_log_record(record):
            return self.log_request(record, config)
        elif record and is_exception_log_record(record):
            return self.log_exception(record, config)

    def format_headers(self, headers):
        return "\n".join(f"{k}: {v}" for k, v in headers.items())
