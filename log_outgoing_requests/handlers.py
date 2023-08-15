# NOTE: Avoid import Django specifics at the module level to prevent circular imports.
# The handler is loaded eagerly at django startup when configuring settings.
import logging
import traceback
from typing import cast
from urllib.parse import urlparse

from .typing import AnyLogRecord, RequestLogRecord, is_request_log_record


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

    def emit(self, record: AnyLogRecord):
        from .models import OutgoingRequestsLog, OutgoingRequestsLogConfig
        from .utils import process_body

        config = OutgoingRequestsLogConfig.get_solo()
        assert isinstance(config, OutgoingRequestsLogConfig)
        if not config.save_logs_enabled:
            return

        # skip requests not coming from the library requests
        if not record or not is_request_log_record(record):
            return
        # Python 3.10 TypeGuard can be useful here
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
