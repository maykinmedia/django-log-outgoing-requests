import logging
from types import TracebackType
from typing import Optional, Tuple, Type, Union

from requests import RequestException
from requests.models import PreparedRequest, Response


class RequestLogRecord(logging.LogRecord):
    req: Optional[PreparedRequest]
    res: Response


class ErrorRequestLogRecord(logging.LogRecord):
    exc_info: Tuple[Type[BaseException], RequestException, Optional[TracebackType]]


AnyLogRecord = Union[logging.LogRecord, RequestLogRecord, ErrorRequestLogRecord]


def is_request_log_record(record: AnyLogRecord) -> bool:
    return getattr(record, "_is_log_outgoing_requests", False)
