"""Global pytest fixtures"""

import logging
from collections.abc import Mapping

import pytest
from requests import Request, Response, Session
from requests.models import CaseInsensitiveDict

from log_outgoing_requests.datastructures import ContentType
from log_outgoing_requests.typing import (
    ErrorRequestLogRecord,
    RequestLogRecord,
    is_request_log_record,
)


#
# default settings
#
@pytest.fixture(autouse=True)
def disable_config_reset(settings):
    settings.LOG_OUTGOING_REQUESTS_RESET_DB_SAVE_AFTER = None


@pytest.fixture
def default_settings(settings):
    settings.LOG_OUTGOING_REQUESTS_CONTENT_TYPES = [
        ContentType(pattern="application/json", default_encoding="utf-8"),
        ContentType(pattern="application/soap+xml", default_encoding="utf-8"),
        ContentType(pattern="application/xml", default_encoding="utf-8"),
        ContentType(pattern="text/xml", default_encoding="iso-8859-1"),
        ContentType(pattern="text/*", default_encoding="utf-8"),
    ]
    return settings


@pytest.fixture
def minimal_settings(settings, mocker):
    settings.LOG_OUTGOING_REQUESTS_DB_SAVE = False
    settings.LOG_OUTGOING_REQUESTS_EMIT_BODY = False
    # can't seem to actually modifiy settings.LOGGING to exclude the handler, since
    # logging is configured in django's setup() phase and is then never run again.
    # Additionally, we can't mock the solo model, since it's a local import...
    mocker.patch(
        "log_outgoing_requests.handlers.DatabaseOutgoingRequestsHandler.emit",
    )


@pytest.fixture
def prepared_request():
    # taken from requests.sessions.request
    req = Request(method="GET", url="https://example.com")
    session = Session()
    return session.prepare_request(req)


class LogRecordEmitter:
    def __call__(
        self,
        method: str = "GET",
        url: str = "https://example.com/some/path",
        headers: Mapping[str, str] = {"Request-Header": "header value"},
        params: Mapping[str, str] = {"queryParam": "one"},
        data: bytes | Mapping[str, str] | None = None,
        response_status: int = 200,
    ) -> RequestLogRecord | ErrorRequestLogRecord:
        record = logging.LogRecord(
            name="log_outgoing_requests",
            level=logging.DEBUG,
            pathname=__file__,
            lineno=1,
            msg="dummy",
            args=None,
            exc_info=None,
        )
        record._is_log_outgoing_requests = True
        prepared_request = Request(
            method=method, url=url, headers=headers, params=params, data=data
        ).prepare()
        assert prepared_request.url

        response = Response()
        response.request = prepared_request
        response.status_code = response_status
        response.headers = CaseInsensitiveDict({"Content-Type": "text/plain"})
        response.encoding = "utf-8"
        response.reason = "OK"
        response._content = "Bòbr".encode()
        response.url = prepared_request.url

        record.req = prepared_request
        record.res = response
        assert is_request_log_record(record)
        return record


@pytest.fixture
def log_record_emitter():
    return LogRecordEmitter()


#
# requests data
#
@pytest.fixture
def request_mock_kwargs():
    return {
        "url": "http://example.com:8000/some-path?version=2.0",
        "status_code": 200,
        "json": {"test": "response data"},
        "request_headers": {
            "Authorization": "test",
            "Content-Type": "application/json",
            "Content-Length": "24",
        },
        "headers": {
            "Date": "Tue, 21 Mar 2023 15:24:08 GMT",
            "Content-Type": "application/json",
            "Content-Length": "25",
        },
    }


@pytest.fixture
def request_mock_kwargs_error():
    return {
        "url": "http://example.com:8000/some-path-that-doesnt-exist?version=2.0",
        "status_code": 404,
        "content": b"404 Not Found",
        "request_headers": {
            "Authorization": "test",
            "Content-Type": "application/json",
            "Content-Length": "24",
        },
        "headers": {
            "Date": "Tue, 21 Mar 2023 15:24:08 GMT",
            "Content-Type": "text/plain",
            "Content-Length": "13",
        },
    }


@pytest.fixture
def request_mock_kwargs_binary():
    return {
        "url": "http://example.com:8000/some-path?version=2.0",
        "status_code": 200,
        "content": b"{\x03\xff\x00d",
        "request_headers": {
            "Authorization": "test",
            "Content-Type": "binary",
        },
        "headers": {
            "Date": "Tue, 21 Mar 2023 15:24:08 GMT",
            "Content-Type": "binary",
        },
    }
