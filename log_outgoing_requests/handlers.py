import logging
import traceback
from urllib.parse import urlparse

from .utils import (
    check_content_length,
    check_content_type,
    get_default_encoding,
    parse_content_type_header,
)


class DatabaseOutgoingRequestsHandler(logging.Handler):
    def emit(self, record):
        from .models import OutgoingRequestsLog, OutgoingRequestsLogConfig

        config = OutgoingRequestsLogConfig.get_solo()

        if config.save_logs_enabled:
            trace = ""

            # skip requests not coming from the library requests
            if not record or not record.getMessage() == "Outgoing request":
                return

            scrubbed_req_headers = record.req.headers.copy()

            if "Authorization" in scrubbed_req_headers:
                scrubbed_req_headers["Authorization"] = "***hidden***"

            if record.exc_info:
                trace = traceback.format_exc()

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
