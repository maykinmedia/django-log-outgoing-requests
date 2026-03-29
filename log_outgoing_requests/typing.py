import logging
from types import TracebackType

from requests import RequestException
from requests.models import PreparedRequest, Response


class RequestLogRecord(logging.LogRecord):
    req: PreparedRequest | None
    res: Response


class ErrorRequestLogRecord(logging.LogRecord):
    exc_info: tuple[type[BaseException], RequestException, TracebackType | None]


AnyLogRecord = logging.LogRecord | RequestLogRecord | ErrorRequestLogRecord


def is_request_log_record(record: AnyLogRecord) -> bool:
    return getattr(record, "_is_log_outgoing_requests", False)
