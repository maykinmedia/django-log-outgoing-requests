import pytest
from requests import RequestException

from log_outgoing_requests.typing import (
    is_error_request_log_record,
    is_request_log_record,
)

from .conftest import LogRecordEmitter


@pytest.mark.parametrize(
    "logger_name",
    [
        "other_logger",
        "log_outgoing_requests.submodule",
    ],
)
def test_is_request_log_record_rejects_non_library_loggers(
    log_record_emitter: LogRecordEmitter, logger_name: str
):
    log_record = log_record_emitter()
    log_record.name = logger_name

    result = is_request_log_record(log_record)

    assert result is False


@pytest.mark.parametrize(
    "logger_name",
    [
        "other_logger",
        "log_outgoing_requests.submodule",
    ],
)
def test_is_error_request_log_record_rejects_non_library_loggers(
    log_record_emitter: LogRecordEmitter, logger_name: str
):
    log_record = log_record_emitter()
    del log_record.req  # type: ignore
    del log_record.res  # type: ignore
    log_record.request_exception = RequestException()
    log_record.name = logger_name

    result = is_error_request_log_record(log_record)

    assert result is False
