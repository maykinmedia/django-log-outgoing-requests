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
        from .utils import (
            check_content_length,
            check_content_type,
            get_default_encoding,
            parse_content_type_header,
        )

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
            content_type, encoding = parse_content_type_header(record.req)
            if check_content_type(content_type) and check_content_length(
                record.req, config
            ):
                kwargs["req_content_type"] = content_type
                kwargs["req_body"] = record.req.body or b""
                kwargs["req_body_encoding"] = encoding or get_default_encoding(
                    content_type
                )

            # check response
            content_type, encoding = parse_content_type_header(record.res)
            if check_content_type(content_type) and check_content_length(
                record.res, config
            ):
                kwargs["res_content_type"] = content_type
                kwargs["res_body"] = record.res.content or b""
                kwargs[
                    "res_body_encoding"
                ] = record.res.encoding or get_default_encoding(content_type)

        OutgoingRequestsLog.objects.create(**kwargs)

    def format_headers(self, headers):
        return "\n".join(f"{k}: {v}" for k, v in headers.items())
