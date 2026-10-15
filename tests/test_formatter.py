"""Tests for the HttpFormatter helper class"""

import io
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
    """
    Assert that request/response bodies are (not) saved if setting is enabled (disabled)
    """

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


def test_formatter_non_requests_exception(caplog, minimal_settings):
    logger = logging.getLogger("log_outgoing_requests")
    with caplog.at_level(logging.DEBUG, logger="log_outgoing_requests"):
        logger.debug(
            "Ignore me",
            extra={"req": None, "res": None},
            exc_info=Exception("Random other exception"),
        )

    record = caplog.records[0]
    formatter = HttpFormatter()
    res = formatter.formatMessage(record)
    assert "-- error --" not in res


@pytest.mark.parametrize(
    "log_body, stream",
    [
        (False, False),
        (False, True),
        (True, True),
    ],
)
def test_formatter_does_not_read_response_body(
    log_record_emitter, settings, log_body, stream
):
    settings.LOG_OUTGOING_REQUESTS_EMIT_BODY = log_body
    record = log_record_emitter(stream=stream)
    # an unread response body, as with ``requests.get(url, stream=True)``
    record.res._content = False
    record.res.raw = io.BytesIO(b"streamed body")

    res = HttpFormatter().format(record)

    assert "200 OK" in res
    assert "streamed body" not in res
    assert record.res.raw.tell() == 0
