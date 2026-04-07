import logging

from requests import RequestException

from log_outgoing_requests.structlog import ExtractRequestAndResponseDetails
from log_outgoing_requests.typing import EventDict, is_request_log_record

from .conftest import LogRecordEmitter

logger = logging.getLogger(__name__)


def _make_event_dict(record: logging.LogRecord) -> EventDict:
    return {
        "_record": record,
        "logger": "log_outgoing_requests",
    }


def test_processor_defaults(log_record_emitter: LogRecordEmitter):
    log_record = log_record_emitter(
        method="POST",
        url="https://example.com/subpath",
        headers={"X-Test": "1", "Content-Type": "text/plain"},
        params={"query": "string"},
        response_status=200,
        data=b"ignored",
    )
    event_dict = _make_event_dict(log_record)
    processor = ExtractRequestAndResponseDetails()

    updated_event_dict = processor(logger, "debug", event_dict)

    # request
    assert updated_event_dict["url"] == "https://example.com/subpath?query=string"
    assert updated_event_dict["method"] == "POST"
    assert updated_event_dict["hostname"] == "example.com"
    assert updated_event_dict["query"] == "query=string"
    assert updated_event_dict["req_headers"] == {
        "X-Test": "1",
        "Content-Type": "text/plain",
        "Content-Length": "7",
    }
    assert "req_content_type" not in updated_event_dict
    assert "req_encoding" not in updated_event_dict
    assert "req_body" not in updated_event_dict
    # response
    assert updated_event_dict["status_code"] == 200
    assert isinstance(updated_event_dict["response_ms"], int)
    assert updated_event_dict["resp_headers"] == {"Content-Type": "text/plain"}
    assert "resp_content_type" not in updated_event_dict
    assert "resp_encoding" not in updated_event_dict
    assert "resp_body" not in updated_event_dict


def test_header_expansion(log_record_emitter: LogRecordEmitter):
    log_record = log_record_emitter(
        method="POST",
        data=rb"{\"key\": 3}",
        headers={"Content-Type": "application/json"},
    )
    event_dict = _make_event_dict(log_record)
    processor = ExtractRequestAndResponseDetails(expand_headers=True)

    updated_event_dict = processor(logger, "debug", event_dict)

    assert "req_header_content_type" in updated_event_dict
    assert updated_event_dict["req_header_content_type"] == "application/json"
    assert "resp_header_content_type" in updated_event_dict


def test_extract_bodies_enabled(log_record_emitter: LogRecordEmitter):
    log_record = log_record_emitter(
        method="POST",
        data=rb"{\"key\": 3}",
        headers={"Content-Type": "application/json"},
    )
    event_dict = _make_event_dict(log_record)
    processor = ExtractRequestAndResponseDetails(extract_bodies=True)

    updated_event_dict = processor(logger, "debug", event_dict)

    assert updated_event_dict["req_content_type"] == "application/json"
    assert updated_event_dict["req_encoding"] == "utf-8"
    assert updated_event_dict["req_body"] == rb"{\"key\": 3}"
    assert updated_event_dict["resp_content_type"] == "text/plain"
    assert updated_event_dict["resp_encoding"] == "utf-8"
    assert updated_event_dict["resp_body"] == "Bòbr".encode()


def test_too_large_bodies_are_not_emitted(log_record_emitter: LogRecordEmitter):
    log_record = log_record_emitter(
        method="POST",
        data=rb"{\"key\": 3}",
        headers={"Content-Type": "application/json"},
    )
    event_dict = _make_event_dict(log_record)
    processor = ExtractRequestAndResponseDetails(
        extract_bodies=True, body_max_content_length=3
    )

    updated_event_dict = processor(logger, "debug", event_dict)

    assert "req_content_type" not in updated_event_dict
    assert "req_encoding" not in updated_event_dict
    assert "req_body" not in updated_event_dict
    assert "resp_content_type" not in updated_event_dict
    assert "resp_encoding" not in updated_event_dict
    assert "resp_body" not in updated_event_dict


def test_extracts_from_errored_requests(log_record_emitter: LogRecordEmitter):
    log_record = log_record_emitter(url="http://errored.request", params={})
    assert is_request_log_record(log_record)
    request = log_record.req
    del log_record.req
    del log_record.res
    log_record.request_exception = RequestException(request=request)
    event_dict = _make_event_dict(log_record)
    processor = ExtractRequestAndResponseDetails()

    updated_event_dict = processor(logger, "debug", event_dict)

    assert updated_event_dict["url"] == "http://errored.request/"
    assert "status_code" not in updated_event_dict


def test_doesnt_crash_on_plain_log_record():
    record = logging.LogRecord(
        name="other_logger",
        level=logging.DEBUG,
        pathname=__file__,
        lineno=1,
        msg="dummy",
        args=None,
        exc_info=None,
    )
    event_dict = _make_event_dict(record)
    processor = ExtractRequestAndResponseDetails()

    updated_event_dict = processor(logger, "debug", event_dict)

    assert updated_event_dict is event_dict


def test_doesnt_crash_on_empty_event_dict():
    processor = ExtractRequestAndResponseDetails()

    updated_event_dict = processor(logger, "debug", {})

    assert updated_event_dict == {}


def test_processor_obfuscates_sensitive_headers(log_record_emitter: LogRecordEmitter):
    log_record = log_record_emitter(
        headers={
            "X-Test": "1",
            "Content-Type": "text/plain",
            "Authorization": "sikrit!",
            "X-API-Key": "ohno",
        },
    )
    event_dict = _make_event_dict(log_record)
    processor = ExtractRequestAndResponseDetails()

    updated_event_dict = processor(logger, "debug", event_dict)

    assert updated_event_dict["req_headers"] == {
        "X-Test": "1",
        "Content-Type": "text/plain",
        "Authorization": "********************",
        "X-API-Key": "********************",
    }
