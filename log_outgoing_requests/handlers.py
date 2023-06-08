# NOTE: Avoid import Django specifics at the module level to prevent circular imports.
# The handler is loaded eagerly at django startup when configuring settings.
import logging
import traceback
from datetime import datetime
from logging import LogRecord
from typing import Union, cast
from urllib.parse import urlparse

from requests.models import PreparedRequest, Response


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


class DatabaseOutgoingRequestsHandler(logging.Handler):
    def emit(self, record: AnyLogRecord):
        from .models import OutgoingRequestsLog, OutgoingRequestsLogConfig
        from .utils import process_body

        config = cast(OutgoingRequestsLogConfig, OutgoingRequestsLogConfig.get_solo())
        if not config.save_logs_enabled:
            return

        # skip requests not coming from the library requests
        if not record or not is_request_log_record(record):
            return
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

    def format_headers(self, headers):
        return "\n".join(f"{k}: {v}" for k, v in headers.items())
