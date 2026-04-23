import logging
import logging.config
import queue
import time
from contextlib import nullcontext
from unittest.mock import patch

import pytest
import requests

from log_outgoing_requests.handlers import (
    DatabaseOutgoingRequestsHandler,
    QueueHandler,
    _queue,
    _stop_listener,
    get_listener,
    outgoing_requests_handler_factory,
)
from log_outgoing_requests.models import OutgoingRequestsLog
from log_outgoing_requests.typing import (
    is_error_request_log_record,
    is_request_log_record,
)

from .conftest import LogRecordEmitter


def assert_background_thread_not_running():
    assert get_listener() is None


@pytest.fixture(autouse=True)
def test_setup_and_teardown(request: pytest.FixtureRequest):
    # prevent connections from being closed for real, since tests run in a transaction
    # and require an open connection for further assertions
    use_real_close_conns = request.node.get_closest_marker("real_db_close")
    patch_context = (
        nullcontext()
        if use_real_close_conns
        else patch("log_outgoing_requests.handlers.close_old_connections")
    )
    with patch_context:
        yield
    _stop_listener()


@pytest.mark.parametrize(
    "use_queue,expected",
    [
        (False, DatabaseOutgoingRequestsHandler),
        (True, QueueHandler),
    ],
)
def test_build_expected_instance_based_on_setting(
    settings, use_queue: bool, expected: type[logging.Handler]
):
    settings.LOG_OUTGOING_REQUESTS_HANDLER_USE_QUEUE = use_queue

    handler = outgoing_requests_handler_factory()

    assert isinstance(handler, expected)
    assert_background_thread_not_running()


@pytest.mark.django_db
def test_handler_flushes_immediately_in_non_queue_mode(
    log_record_emitter: LogRecordEmitter,
):
    handler = DatabaseOutgoingRequestsHandler(
        buffer_size=1000,
        flush_interval=999,
        use_queue_mode=False,
    )
    log_record = log_record_emitter(url="https://1670.pl/kurwa")

    result = handler.handle(log_record)

    assert result is not False
    logs = OutgoingRequestsLog.objects.all()
    assert len(logs) == 1
    assert logs[0].url == "https://1670.pl/kurwa?queryParam=one"


@pytest.mark.django_db
def test_handler_flushes_in_queue_mode_when_buffer_size_limit_reached(
    log_record_emitter: LogRecordEmitter,
    subtests: pytest.Subtests,
):
    handler = DatabaseOutgoingRequestsHandler(
        buffer_size=2,
        flush_interval=999,
        use_queue_mode=True,
    )
    log_record = log_record_emitter()

    with subtests.test("buffer not yet full"):
        result = handler.handle(log_record)

        assert result is not False
        logs = OutgoingRequestsLog.objects.all()
        assert len(logs) == 0

    with subtests.test("buffer full"):
        result = handler.handle(log_record)

        assert result is not False
        logs = OutgoingRequestsLog.objects.all()
        assert len(logs) == 2


@pytest.mark.django_db
def test_handler_flushes_in_queue_mode_when_flush_interval_is_exceeded(
    log_record_emitter: LogRecordEmitter,
    subtests: pytest.Subtests,
):
    handler = DatabaseOutgoingRequestsHandler(
        buffer_size=999,
        flush_interval=0.5,
        use_queue_mode=True,
    )
    log_record = log_record_emitter()

    with subtests.test("buffer not full, last write recent enough"):
        result = handler.handle(log_record)

        assert result is not False
        logs = OutgoingRequestsLog.objects.all()
        assert len(logs) == 0

    time.sleep(0.5)

    with subtests.test("buffer not full, last write too long ago"):
        result = handler.handle(log_record)

        assert result is not False
        logs = OutgoingRequestsLog.objects.all()
        assert len(logs) == 2


@pytest.mark.django_db
def test_closing_handler_flushes_the_queue(log_record_emitter: LogRecordEmitter):
    handler = DatabaseOutgoingRequestsHandler(
        buffer_size=999,
        flush_interval=999,
        use_queue_mode=True,
    )
    log_record = log_record_emitter()
    result = handler.handle(log_record)

    assert result is not False
    assert not OutgoingRequestsLog.objects.exists()

    handler.close()

    assert OutgoingRequestsLog.objects.count() == 1


@pytest.mark.django_db
def test_handler_can_be_disabled_with_setting(
    settings,
    log_record_emitter: LogRecordEmitter,
):
    settings.LOG_OUTGOING_REQUESTS_DB_SAVE = False
    handler = DatabaseOutgoingRequestsHandler(
        buffer_size=999,
        flush_interval=999,
        use_queue_mode=False,
    )
    log_record = log_record_emitter()

    result = handler.handle(log_record)

    assert result is not False
    assert not OutgoingRequestsLog.objects.exists()


@pytest.mark.django_db
def test_handler_calls_on_error_callback_if_provided(
    settings,
    log_record_emitter: LogRecordEmitter,
):
    errors_seen: set[Exception] = set()
    settings.LOG_OUTGOING_REQUESTS_HANDLER_ON_ERROR = lambda err: errors_seen.add(err)
    log_record = log_record_emitter()
    log_record.req.url = None  # type: ignore we're breaking it on purpose
    handler = DatabaseOutgoingRequestsHandler(use_queue_mode=False)

    result = handler.handle(log_record)

    assert result is not False
    assert len(errors_seen) == 1


def test_queue_handler_plain_log_records():
    # log record masquerading as request log record, but it's missing the request
    # attributes
    record = logging.LogRecord(
        name="log_outgoing_requests",
        level=logging.DEBUG,
        pathname=__file__,
        lineno=1,
        msg="dummy",
        args=None,
        exc_info=None,
    )
    test_queue = queue.Queue(maxsize=1)
    handler = QueueHandler(test_queue)

    handler.handle(record)

    with pytest.raises(queue.Empty):
        test_queue.get_nowait()


def test_queue_handler_request_exception_record_without_response(
    log_record_emitter: LogRecordEmitter,
):
    log_record = log_record_emitter()
    assert is_request_log_record(log_record)
    log_record.request_exception = requests.RequestException(
        request=log_record.req,
        response=None,
    )
    del log_record.req
    del log_record.res
    assert is_error_request_log_record(log_record)
    test_queue = queue.Queue(maxsize=1)
    handler = QueueHandler(test_queue)

    handler.handle(log_record)

    queued_record = test_queue.get_nowait()
    assert queued_record is log_record


@pytest.fixture
def enable_background_thread_logging(settings, monkeypatch: pytest.MonkeyPatch):
    settings.LOG_OUTGOING_REQUESTS_HANDLER_USE_QUEUE = True
    monkeypatch.setenv("_LOG_OUTGOING_REQUESTS_LOGGER_DEFER_LISTENER", "false")
    logging.config.dictConfig(
        {
            "version": 1,
            "disable_existing_loggers": False,
            "handlers": {
                "log_outgoing_requests": {
                    "level": "DEBUG",
                    "()": (
                        "log_outgoing_requests.handlers"
                        ".outgoing_requests_handler_factory"
                    ),
                    "buffer_size": 1,  # force immediate flush
                    "flush_interval": 1,
                },
            },
            "loggers": {
                "log_outgoing_requests": {
                    "handlers": ["log_outgoing_requests"],
                    "level": "DEBUG",
                    "propagate": False,
                }
            },
        }
    )
    assert get_listener() is not None

    try:
        yield
    finally:
        # restore original config
        logging.config.dictConfig(settings.LOGGING)


@pytest.mark.real_db_close
@pytest.mark.django_db(transaction=True)
def test_integration_via_logging_dictconfig(
    settings,
    monkeypatch: pytest.MonkeyPatch,
    requests_mock,
    request_mock_kwargs,
    enable_background_thread_logging,
):
    requests_mock.get(**request_mock_kwargs)

    requests.get(
        request_mock_kwargs["url"],
        headers=request_mock_kwargs["request_headers"],
    )

    _queue.join()

    assert OutgoingRequestsLog.objects.count() == 1
    log_obj = OutgoingRequestsLog.objects.get()
    assert log_obj.url == request_mock_kwargs["url"]


@pytest.mark.live_http
@pytest.mark.real_db_close
@pytest.mark.django_db(transaction=True)
def test_logging_of_gzipped_response_is_thread_safe(
    settings,
    monkeypatch: pytest.MonkeyPatch,
    enable_background_thread_logging,
):
    # Make sure to spin up the docker-compose.yml in the root of the repository, as a
    # live HTTP service is required:
    #
    #   docker compose up
    #
    settings.LOG_OUTGOING_REQUESTS_MAX_CONTENT_LENGTH = 1024**3  # 1 MiB

    def _make_gzip_request():
        response = requests.get("http://localhost:8080/gzip.txt")
        assert response.headers["Transfer-Encoding"] == "chunked"
        assert response.headers["Content-Encoding"] == "gzip"
        assert "Content-Length" not in response.headers
        # consume the body
        assert len(response.content) > 0

    # this errors reliably-enough with a large enough response body, see the docker
    # compose config
    _make_gzip_request()

    _queue.join()

    assert OutgoingRequestsLog.objects.count() == 1
    log_obj = OutgoingRequestsLog.objects.get()
    assert log_obj.url == "http://localhost:8080/gzip.txt"
    assert log_obj.response_content_length > 0
    assert b"abcdefghijklmnopqrstuvwxyz0123456789" in log_obj.res_body


@pytest.mark.live_http
@pytest.mark.real_db_close
@pytest.mark.django_db(transaction=True)
def test_logging_of_gzipped_response_with_streaming_is_skipped_to_avoid_memory_impact(
    settings,
    monkeypatch: pytest.MonkeyPatch,
    enable_background_thread_logging,
):
    # Make sure to spin up the docker-compose.yml in the root of the repository, as a
    # live HTTP service is required:
    #
    #   docker compose up
    #
    settings.LOG_OUTGOING_REQUESTS_MAX_CONTENT_LENGTH = 1024**3  # 1 MiB

    def _make_streaming_request():
        # make a request in streaming mode and validate that the content can be consumed
        response = requests.get("http://localhost:8080/gzip.txt", stream=True)
        assert response.status_code == 200
        assert response.headers["Transfer-Encoding"] == "chunked"
        assert response.headers["Content-Encoding"] == "gzip"
        assert "Content-Length" not in response.headers

        # consume the body
        num_chunks = 0
        for _ in response.iter_content(chunk_size=1024 * 8):  # 8 KiB chunks
            num_chunks += 1

        assert num_chunks > 0

    # this errors reliably-enough with a large enough response body, see the docker
    # compose config
    _make_streaming_request()

    _queue.join()

    # we do expect the metadata to be logged, but no body to be logged
    assert OutgoingRequestsLog.objects.count() == 1
    log_obj = OutgoingRequestsLog.objects.get()
    assert log_obj.url == "http://localhost:8080/gzip.txt"
    assert not log_obj.response_content_length
    assert log_obj.res_body == b""
