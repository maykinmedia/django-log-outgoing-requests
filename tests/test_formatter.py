"""Tests for the HttpFormatter helper class"""

import logging

import pytest
import requests

from log_outgoing_requests.formatters import HttpFormatter


@pytest.mark.django_db
@pytest.mark.parametrize(
    "log_body, expected",
    [
        (True, True),
        (False, False),
    ],
)
def test_formatter(
    requests_mock,
    request_mock_kwargs,
    caplog,
    settings,
    log_body,
    expected,
):
    """Assert that request/response bodies are (not) saved if setting is enabled (disabled)"""

    settings.LOG_OUTGOING_REQUESTS_EMIT_BODY = log_body

    formatter = HttpFormatter()

    with caplog.at_level(logging.DEBUG):
        requests_mock.post(**request_mock_kwargs)
        requests.post(
            request_mock_kwargs["url"],
            headers=request_mock_kwargs["request_headers"],
            json={"test": "request data"},
        )

    record = caplog.records[1]

    res = formatter.formatMessage(record)

    assert ('{"test": "request data"}' in res) is expected
    assert ('{"test": "response data"}' in res) is expected
