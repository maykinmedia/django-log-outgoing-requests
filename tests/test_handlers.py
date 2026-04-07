import logging
import logging.config
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


@pytest.fixture
def _restore_logging_config(settings):
    try:
        yield
    finally:
        logging.config.dictConfig(settings.LOGGING)


@pytest.mark.real_db_close
@pytest.mark.django_db(transaction=True)
def test_integration_via_logging_dictconfig(
    settings,
    monkeypatch: pytest.MonkeyPatch,
    requests_mock,
    request_mock_kwargs,
    _restore_logging_config,
):
    settings.LOG_OUTGOING_REQUESTS_HANDLER_USE_QUEUE = True
    monkeypatch.setenv("_LOG_OUTGOING_REQUESTS_LOGGER_DEFER_LISTENER", "false")
    requests_mock.get(**request_mock_kwargs)
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

    requests.get(
        request_mock_kwargs["url"],
        headers=request_mock_kwargs["request_headers"],
    )

    _queue.join()

    assert OutgoingRequestsLog.objects.count() == 1
    log_obj = OutgoingRequestsLog.objects.get()
    assert log_obj.url == request_mock_kwargs["url"]
