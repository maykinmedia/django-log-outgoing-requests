import logging
from datetime import datetime
from typing import Optional, Union

from requests.models import PreparedRequest, Response


class RequestLogRecord(logging.LogRecord):
    requested_at: datetime
    req: Optional[PreparedRequest]
    res: Optional[Response]


AnyLogRecord = Union[logging.LogRecord, RequestLogRecord]


def is_request_log_record(record: AnyLogRecord) -> bool:
    attrs = ("requested_at", "req", "res")
    if any(not hasattr(record, attr) for attr in attrs):
        return False
    return True
