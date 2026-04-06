from __future__ import annotations

import logging
from collections.abc import MutableMapping
from typing import Any

from requests import RequestException
from requests.models import PreparedRequest, Response
from typing_extensions import TypeIs


class RequestLogRecord(logging.LogRecord):
    """
    A log record produced by the request logging hook.
    """

    req: PreparedRequest
    res: Response


class ErrorRequestLogRecord(logging.LogRecord):
    """
    A log record produced by the request exception logging wrapper.
    """

    request_exception: RequestException


AnyLogRecord = logging.LogRecord | RequestLogRecord | ErrorRequestLogRecord


def is_any_request_log_record(
    record: AnyLogRecord,
) -> TypeIs[RequestLogRecord | ErrorRequestLogRecord]:
    """
    Test if the provided log record is a log record emitted for a request.

    Request logs are always emitted by the package/module name logger. Note that
    submodules may also produce log records, but their name will be something
    like log_outgoing_requests.handlers
    """
    if record.name != "log_outgoing_requests":
        return False
    return is_request_log_record(record) or is_error_request_log_record(record)


def is_request_log_record(record: AnyLogRecord) -> TypeIs[RequestLogRecord]:
    if record.name != "log_outgoing_requests":
        return False
    req = getattr(record, "req", None)
    res = getattr(record, "res", None)

    # we need to support duck typing and can't isinstance(req, PreparedRequest) due
    # to requests-mock replacing that with _RequestObjectProxy in tests...
    _is_request_like = hasattr(req, "method") and hasattr(req, "url")
    return _is_request_like and isinstance(res, Response)


def is_error_request_log_record(record: AnyLogRecord) -> TypeIs[ErrorRequestLogRecord]:
    if record.name != "log_outgoing_requests":
        return False
    exception = getattr(record, "request_exception", None)
    return isinstance(exception, RequestException)


type EventDict = MutableMapping[str, Any]
"""
Structlog's ``EventDict`` type, vendored to avoid a dependency.

See upstream: https://github.com/hynek/structlog/blob/811245fe02fcf454f517f0677648457bfec52ef0/src/structlog/typing.py#L57
"""
