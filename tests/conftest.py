"""Global pytest fixtures"""

import pytest

from log_outgoing_requests.datastructures import ContentType


#
# default settings
#
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
def minimal_settings(settings):
    settings.LOG_OUTGOING_REQUESTS_DB_SAVE = False
    settings.LOG_OUTGOING_REQUESTS_EMIT_BODY = False


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
