import logging

import pytest
import requests
from requests import RequestException

from log_outgoing_requests.formatters import HttpFormatter
from log_outgoing_requests.log_requests import log_errors
from log_outgoing_requests.models import OutgoingRequestsLog


def test_invalid_dns_name_error(minimal_settings, caplog):
    # use bogus DNS name that should not resolve anywhere. We want the real requests
    # behaviour here with the exact exceptions raised.
    caplog.set_level(logging.DEBUG, logger="log_outgoing_requests")
    with pytest.raises(RequestException):
        requests.get("https://e57f27db-ef2f-4475-98e8-cb3a4409cb3f")

    assert len(caplog.records) == 1
    assert "Outgoing request error" in caplog.text


def test_any_requests_exception_logged(minimal_settings, caplog, requests_mock):
    caplog.set_level(logging.DEBUG, logger="log_outgoing_requests")

    # use locally scoped exception to check that the error handling mechanism can handle
    # any requests.RequestException
    class LocallyScopedException(RequestException):
        pass

    requests_mock.get(
        "https://example.com", exc=LocallyScopedException("must be logged")
    )

    with pytest.raises(RequestException):
        requests.get("https://example.com")

    assert len(caplog.records) == 1
    assert "Outgoing request error" in caplog.text


def test_properly_emit_exception_logs(prepared_request, minimal_settings, caplog):
    caplog.set_level(logging.DEBUG, logger="log_outgoing_requests")
    formatter = HttpFormatter()

    with pytest.raises(RequestException):
        with log_errors():
            raise RequestException("Something went wrong!", request=prepared_request)

    assert len(caplog.records) == 1
    record = caplog.records[0]
    res = formatter.formatMessage(record)

    assert "Something went wrong!" in res


def test_properly_format_http_error_responses(minimal_settings, caplog, requests_mock):
    caplog.set_level(logging.DEBUG, logger="log_outgoing_requests")
    requests_mock.get(
        "https://example.com", status_code=500, reason="Internal Server Error"
    )

    requests.get("https://example.com")

    assert len(caplog.records) == 1
    record = caplog.records[0]
    formatter = HttpFormatter()
    res = formatter.formatMessage(record)

    assert "---------------- response ----------------" in res
    assert "500 Internal Server Error https://example.com" in res


@pytest.mark.django_db
def test_errored_request_error_information_recorded_in_db():
    with pytest.raises(RequestException):
        requests.get("https://e57f27db-ef2f-4475-98e8-cb3a4409cb3f")

    request_log = OutgoingRequestsLog.objects.get()

    assert request_log.url == "https://e57f27db-ef2f-4475-98e8-cb3a4409cb3f/"
    assert request_log.method == "GET"
    assert request_log.trace != ""
    assert request_log.status_code is None
    assert request_log.response_ms == 0
