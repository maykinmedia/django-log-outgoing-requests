"""Integration tests for the core functionality of the library"""

import logging

import pytest
import requests
from freezegun import freeze_time

from log_outgoing_requests.datastructures import ContentType
from log_outgoing_requests.models import OutgoingRequestsLog


#
# Local pytest fixtures
#
@pytest.fixture()
def request_variants(requests_mock):
    return [
        ("GET", requests.get, requests_mock.get),
        ("POST", requests.post, requests_mock.post),
        ("PUT", requests.put, requests_mock.put),
        ("PATCH", requests.patch, requests_mock.patch),
        ("DELETE", requests.delete, requests_mock.delete),
        ("HEAD", requests.head, requests_mock.head),
    ]


@pytest.fixture()
def expected_headers():
    return (
        f"User-Agent: python-requests/{requests.__version__}\n"
        "Accept-Encoding: gzip, deflate\n"
        "Accept: */*\n"
        "Connection: keep-alive\n"
        "Authorization: ***hidden***\n"
        "Content-Type: application/json\n"
        "Content-Length: 24"
    )


#
# Tests
#
@pytest.mark.django_db
def test_data_is_logged(requests_mock, request_mock_kwargs, caplog):
    with caplog.at_level(logging.DEBUG):
        requests_mock.get(**request_mock_kwargs)
        requests.get(
            request_mock_kwargs["url"], headers=request_mock_kwargs["request_headers"]
        )

    records = caplog.records
    assert records[1].levelname == "DEBUG"
    assert records[1].name == "log_outgoing_requests"
    assert records[1].msg == "Outgoing request"


@pytest.mark.django_db
def test_log_only_once(requests_mock, request_mock_kwargs, caplog):
    requests_mock.get("https://example.com", status_code=200)

    with caplog.at_level(logging.DEBUG, logger="log_outgoing_requests"):
        with requests.Session() as session:
            # 2 calls -> expect 2 log records and 2 DB records
            session.get("https://example.com")
            session.get("https://example.com")

    assert len(caplog.records) == 2
    db_records = OutgoingRequestsLog.objects.all()
    assert db_records.count() == 2


@pytest.mark.django_db
@freeze_time("2021-10-18 13:00:00")
def test_data_is_saved(request_mock_kwargs, request_variants, expected_headers):
    for method, request_func, request_mock in request_variants:
        request_mock(**request_mock_kwargs)
        response = request_func(
            request_mock_kwargs["url"],
            headers=request_mock_kwargs["request_headers"],
            json={"test": "request data"},
        )

        assert response.status_code == 200

        request_log = OutgoingRequestsLog.objects.last()

        assert request_log.method == method
        assert request_log.hostname == "example.com:8000"
        assert request_log.params == ""
        assert request_log.query_params == "version=2.0"
        assert request_log.response_ms == 0
        assert request_log.trace == ""
        assert str(request_log) == "example.com:8000 at 2021-10-18 13:00:00+00:00"
        assert (
            request_log.timestamp.strftime("%Y-%m-%d %H:%M:%S") == "2021-10-18 13:00:00"
        )
        # headers
        assert request_log.req_headers == expected_headers
        assert (
            request_log.res_headers == "Date: Tue, 21 Mar 2023 15:24:08 GMT\n"
            "Content-Type: application/json\nContent-Length: 25"
        )
        # request body
        assert request_log.req_content_type == "application/json"
        assert bytes(request_log.req_body) == b'{"test": "request data"}'
        assert request_log.req_body_encoding == "utf-8"
        # response body
        assert request_log.res_content_type == "application/json"
        assert bytes(request_log.res_body) == b'{"test": "response data"}'
        assert request_log.res_body_encoding == "utf-8"


#
# test decoding of binary content
#
@pytest.mark.parametrize(
    "content, encoding, expected",
    [
        (b"test\x03\xff\xff{\x03}", "utf-8", "test\x03��{\x03}"),
        (b"test\x03\xff\xff{\x03}", "utx-99", "test\x03��{\x03}"),
        (b"test{\x03\xff\xff\x00d", "", "test{\x03��\x00d"),
    ],
)
@pytest.mark.django_db
def test_decoding_of_binary_content(
    content, encoding, expected, requests_mock, request_mock_kwargs_binary, settings
):
    """
    Assert that decoding of binary contents works with:
        - correct encoding
        - wrong (e.g. misspelled) encoding
        - missing encoding
    """
    settings.LOG_OUTGOING_REQUESTS_CONTENT_TYPES = [
        ContentType(pattern="binary", default_encoding=encoding)
    ]

    request_mock_kwargs_binary["content"] = content

    requests_mock.post(**request_mock_kwargs_binary)
    response = requests.post(
        request_mock_kwargs_binary["url"],
        headers=request_mock_kwargs_binary["request_headers"],
        data=content,
    )

    assert response.status_code == 200

    request_log = OutgoingRequestsLog.objects.last()

    assert request_log.response_body_decoded == expected
    assert request_log.request_body_decoded == expected


@pytest.mark.django_db
def test_authorization_header_is_hidden(requests_mock, request_mock_kwargs):
    requests_mock.get(**request_mock_kwargs)
    requests.get(
        request_mock_kwargs["url"], headers=request_mock_kwargs["request_headers"]
    )

    log = OutgoingRequestsLog.objects.get()

    assert "Authorization: ***hidden***" in log.req_headers


@pytest.mark.django_db
def test_disable_save_db(request_mock_kwargs, request_variants, caplog, settings):
    """Assert that data is logged but not saved to DB when setting is disabled"""

    settings.LOG_OUTGOING_REQUESTS_DB_SAVE = False

    for method, request_func, request_mock in request_variants:
        with caplog.at_level(logging.DEBUG):
            request_mock(**request_mock_kwargs)
            response = request_func(
                request_mock_kwargs["url"],
                headers=request_mock_kwargs["request_headers"],
                json={"test": "request data"},
            )

            assert response.status_code == 200

            # data is logged
            records = caplog.records
            assert records[1].levelname == "DEBUG"
            assert records[1].name == "log_outgoing_requests"
            assert records[1].msg == "Outgoing request"

            # data is not saved
            assert OutgoingRequestsLog.objects.exists() is False


@pytest.mark.django_db
def test_disable_save_body(request_mock_kwargs, request_variants, settings):
    """Assert that request/response bodies are not saved when setting is disabled"""

    settings.LOG_OUTGOING_REQUESTS_DB_SAVE_BODY = False

    for method, request_func, request_mock in request_variants:
        request_mock(**request_mock_kwargs)
        response = request_func(
            request_mock_kwargs["url"],
            headers=request_mock_kwargs["request_headers"],
            json={"test": "request data"},
        )

        assert response.status_code == 200

        request_log = OutgoingRequestsLog.objects.last()

        assert bytes(request_log.req_body) == b""
        assert bytes(request_log.res_body) == b""


@pytest.mark.django_db
def test_content_type_not_allowed(request_mock_kwargs, request_variants, settings):
    """Assert that request/response bodies are not saved when content type is not allowed"""

    settings.LOG_OUTGOING_REQUESTS_CONTENT_TYPES = [
        ContentType(pattern="text/*", default_encoding="utf-8")
    ]

    for method, request_func, request_mock in request_variants:
        request_mock(**request_mock_kwargs)
        response = request_func(
            request_mock_kwargs["url"],
            headers=request_mock_kwargs["request_headers"],
            json={"test": "request data"},
        )

        assert response.status_code == 200

        request_log = OutgoingRequestsLog.objects.last()

        assert bytes(request_log.req_body) == b""
        assert bytes(request_log.res_body) == b""


@pytest.mark.django_db
def test_content_length_exceeded(request_mock_kwargs, request_variants, settings):
    """Assert that body is not saved when content-length exceeds pre-defined max"""

    settings.LOG_OUTGOING_REQUESTS_MAX_CONTENT_LENGTH = 10

    for method, request_func, request_mock in request_variants:
        request_mock(**request_mock_kwargs)
        response = request_func(
            request_mock_kwargs["url"],
            headers=request_mock_kwargs["request_headers"],
            json={"test": "request data"},
        )

        assert response.status_code == 200

        request_log = OutgoingRequestsLog.objects.last()

        assert bytes(request_log.res_body) == b""


def test_unexpected_exceptions_do_not_crash_entire_application(mocker, requests_mock):
    # let's pretend that get_solo is broken, perhaps because the cache is not reachable...
    mocker.patch(
        "solo.models.SingletonModel.get_solo",
        side_effect=Exception("Oh no, solo broke!"),
    )
    requests_mock.get("https://example.com")

    try:
        requests.get("https://example.com")
    except Exception:
        pytest.fail(
            "Regular operation should not fatally crash because of logging issues."
        )
