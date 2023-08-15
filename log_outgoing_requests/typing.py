import logging
from datetime import datetime
from typing import Union

from requests.models import PreparedRequest, Response


class RequestLogRecord(logging.LogRecord):
    requested_at: datetime
    req: PreparedRequest | None
    res: Response | None


AnyLogRecord = Union[logging.LogRecord, RequestLogRecord]


def is_request_log_record(record: AnyLogRecord) -> bool:
    attrs = ("requested_at", "req", "res")
    if any(not hasattr(record, attr) for attr in attrs):
        return False
    return True
