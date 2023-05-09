import logging
import traceback
from urllib.parse import urlparse

from django.conf import settings

ALLOWED_CONTENT_TYPES = [
    "application/json",
    "multipart/form-data",
    "text/html",
    "text/plain",
    "",
    None,
]


class DatabaseOutgoingRequestsHandler(logging.Handler):
    def emit(self, record):
        from .models import OutgoingRequestsLogConfig

        config = OutgoingRequestsLogConfig.get_solo()

        if config.save_to_db or settings.LOG_OUTGOING_REQUESTS_DB_SAVE:
            from .models import OutgoingRequestsLog

            trace = None

            # skip requests not coming from the library requests
            if not record or not record.getMessage() == "Outgoing request":
                return

            # skip requests with non-allowed content
            request_content_type = record.req.headers.get("Content-Type", "")
            response_content_type = record.res.headers.get("Content-Type", "")

            if not (
                request_content_type in ALLOWED_CONTENT_TYPES
                and response_content_type in ALLOWED_CONTENT_TYPES
            ):
                return

            safe_req_headers = record.req.headers.copy()

            if "Authorization" in safe_req_headers:
                safe_req_headers["Authorization"] = "***hidden***"

            if record.exc_info:
                trace = traceback.format_exc()

            parsed_url = urlparse(record.req.url)
            kwargs = {
                "url": record.req.url,
                "hostname": parsed_url.hostname,
                "params": parsed_url.params,
                "status_code": record.res.status_code,
                "method": record.req.method,
                "req_content_type": record.req.headers.get("Content-Type", ""),
                "res_content_type": record.res.headers.get("Content-Type", ""),
                "timestamp": record.requested_at,
                "response_ms": int(record.res.elapsed.total_seconds() * 1000),
                "req_headers": self.format_headers(safe_req_headers),
                "res_headers": self.format_headers(record.res.headers),
                "trace": trace,
            }

            if config.save_body or settings.LOG_OUTGOING_REQUESTS_SAVE_BODY:
                kwargs["req_body"] = (record.req.body,)
                kwargs["res_body"] = (record.res.json(),)

            OutgoingRequestsLog.objects.create(**kwargs)

    def format_headers(self, headers):
        return "\n".join(f"{k}: {v}" for k, v in headers.items())
