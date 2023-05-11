"""Tests for the utility functions"""

import logging

import pytest
import requests

from log_outgoing_requests.datastructures import ContentType
from log_outgoing_requests.models import OutgoingRequestsLogConfig
from log_outgoing_requests.utils import (
    check_content_length,
    check_content_type,
    get_default_encoding,
    parse_content_type_header,
)


#
# test check_content_length
#
@pytest.mark.parametrize(
    "max_content_length, expected",
    [
        (1048, True),
        (12, False),
    ],
)
@pytest.mark.django_db
def test_check_content_length(
    max_content_length,
    requests_mock,
    request_mock_kwargs,
    expected,
):
    config = OutgoingRequestsLogConfig.objects.create(
        max_content_length=max_content_length,
    )

    # we check the functionality of determining missing content length
    # only for the response (the requests library automatically inserts
    # the content length for the request)
    del request_mock_kwargs["headers"]["Content-Length"]

    mock = requests_mock.post(**request_mock_kwargs)
    response = requests.post(
        request_mock_kwargs["url"],
        headers=request_mock_kwargs["request_headers"],
        json={"test": "request data"},
    )

    assert response.status_code == 200

    result_request = check_content_length(mock.last_request, config=config)
    assert result_request is expected

    result_response = check_content_length(response, config=config)
    assert result_response is expected


#
# test parse_content_type_header
#
@pytest.mark.parametrize(
    "content_type_header, expected_content_type, expected_encoding",
    [
        ("text/xml; charset=us-ascii", "text/xml", "us-ascii"),
        ("text/xml", "text/xml", ""),
        ("application/json", "application/json", ""),
        ("", "", ""),
    ],
)
@pytest.mark.django_db
def test_parse_content_type_header(
    content_type_header,
    requests_mock,
    request_mock_kwargs,
    expected_content_type,
    expected_encoding,
):
    request_mock_kwargs["request_headers"]["Content-Type"] = content_type_header
    request_mock_kwargs["headers"]["Content-Type"] = content_type_header

    mock = requests_mock.post(**request_mock_kwargs)
    response = requests.post(
        request_mock_kwargs["url"],
        headers=request_mock_kwargs["request_headers"],
        json={"test": "request data"},
    )

    assert response.status_code == 200

    # check request
    parsed_request_header = parse_content_type_header(mock.last_request)
    assert parsed_request_header[0] == expected_content_type
    assert parsed_request_header[1] == expected_encoding

    # check response
    parsed_response_header = parse_content_type_header(response)
    assert parsed_response_header[0] == expected_content_type
    assert parsed_response_header[1] == expected_encoding


#
# test check_content_type
#
@pytest.mark.parametrize(
    "allowed_content_types, content_type_pattern, expected",
    [
        ([ContentType("text/xml", "iso-8859-1")], "text/xml", True),
        ([ContentType("text/xml", "iso-8859-1")], "text/html", False),
        ([ContentType("text/xml", "iso-8859-1")], "video/mp4", False),
        ([ContentType("text/*", "utf-8")], "text/html", True),
    ],
)
@pytest.mark.django_db
def test_check_content_type(
    allowed_content_types,
    content_type_pattern,
    expected,
    settings,
):
    settings.LOG_OUTGOING_REQUESTS_CONTENT_TYPES = allowed_content_types

    result = check_content_type(content_type_pattern)
    assert result is expected


#
# test get_default_encoding
#
@pytest.mark.parametrize(
    "content_type_pattern, expected",
    [
        ("text/html", "utf-8"),
        ("text/xml", "iso-8859-1"),
        ("application/json", "utf-8"),
        ("application/unknown", ""),
    ],
)
@pytest.mark.django_db
def test_get_default_encoding(
    content_type_pattern,
    expected,
):
    result = get_default_encoding(content_type_pattern)
    assert result == expected


@pytest.mark.django_db
def test_logger_warning_missing_content_length(
    requests_mock, request_mock_kwargs, caplog
):
    del request_mock_kwargs["request_headers"]["Content-Length"]

    with caplog.at_level(logging.DEBUG):
        requests_mock.get(**request_mock_kwargs)
        requests.get(
            request_mock_kwargs["url"], headers=request_mock_kwargs["request_headers"]
        )

    records = caplog.records
    assert records[1].levelname == "WARNING"
    assert records[1].name == "log_outgoing_requests.utils"
    assert (
        records[1].msg
        == "Content length of the request/response (request netloc: example.com:8000) could not be determined."
    )
