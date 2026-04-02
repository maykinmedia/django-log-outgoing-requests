from __future__ import annotations

import logging
from collections.abc import MutableMapping
from types import TracebackType
from typing import Any

from requests import RequestException
from requests.models import PreparedRequest, Response
from typing_extensions import TypeIs


class RequestLogRecord(logging.LogRecord):
    req: PreparedRequest | None
    res: Response


class ErrorRequestLogRecord(logging.LogRecord):
    exc_info: tuple[type[BaseException], RequestException, TracebackType | None]


AnyLogRecord = logging.LogRecord | RequestLogRecord | ErrorRequestLogRecord


def is_request_log_record(
    record: AnyLogRecord,
) -> TypeIs[RequestLogRecord | ErrorRequestLogRecord]:
    # FIXME: remove marker but test that the right logger is used.
    return getattr(record, "_is_log_outgoing_requests", False)


def is_request_without_error_record(
    record: RequestLogRecord | ErrorRequestLogRecord,
) -> TypeIs[RequestLogRecord]:
    return getattr(record, "res", None) is not None


def is_error_request_log_record(
    record: RequestLogRecord | ErrorRequestLogRecord,
) -> TypeIs[ErrorRequestLogRecord]:
    exception = record.exc_info[1] if record.exc_info else None
    return isinstance(exception, RequestException)


type EventDict = MutableMapping[str, Any]
"""
Structlog's ``EventDict`` type, vendored to avoid a dependency.

See upstream: https://github.com/hynek/structlog/blob/811245fe02fcf454f517f0677648457bfec52ef0/src/structlog/typing.py#L57
"""


def is_event_dict(msg: str | Any) -> TypeIs[EventDict]:
    """
    Test if the provided log record message is an event dict.
    """
    return isinstance(msg, dict)
