import logging
from io import StringIO

from django.core.management import call_command
from django.utils import timezone

import pytest
import requests
from freezegun import freeze_time

from log_outgoing_requests.config_reset import schedule_config_reset
from log_outgoing_requests.models import OutgoingRequestsLog, OutgoingRequestsLogConfig

try:
    import celery
except ImportError:
    celery = None

has_celery = celery is not None


@pytest.mark.django_db
def test_cleanup_request_logs_command(settings, caplog):
    settings.LOG_OUTGOING_REQUESTS_MAX_AGE = 1  # delete if > 1 day old

    with freeze_time("2023-10-02T12:00:00Z") as frozen_time:
        OutgoingRequestsLog.objects.create(timestamp=timezone.now())
        frozen_time.move_to("2023-10-04T12:00:00Z")
        recent_log = OutgoingRequestsLog.objects.create(timestamp=timezone.now())

        stdout = StringIO()
        with caplog.at_level(logging.INFO):
            call_command(
                "prune_outgoing_request_logs", stdout=stdout, stderr=StringIO()
            )

    output = stdout.getvalue()
    assert output == "Deleted 1 outgoing request log(s)\n"

    assert OutgoingRequestsLog.objects.get() == recent_log


@pytest.mark.skipif(not has_celery, reason="Celery is optional dependency")
@pytest.mark.django_db
def test_cleanup_request_logs_celery_task(requests_mock, settings, caplog):
    from log_outgoing_requests.tasks import prune_logs

    settings.LOG_OUTGOING_REQUESTS_MAX_AGE = 1  # delete if > 1 old old

    with freeze_time("2023-10-02T12:00:00Z") as frozen_time:
        OutgoingRequestsLog.objects.create(timestamp=timezone.now())
        frozen_time.move_to("2023-10-04T12:00:00Z")
        recent_log = OutgoingRequestsLog.objects.create(timestamp=timezone.now())

        with caplog.at_level(logging.INFO):
            prune_logs()

    assert len(caplog.records) == 1
    assert "Deleted 1 outgoing request log(s)" in caplog.text

    assert OutgoingRequestsLog.objects.get() == recent_log


@pytest.mark.skipif(not has_celery, reason="Celery is optional dependency")
@pytest.mark.django_db
def test_reset_config(requests_mock, settings):
    from log_outgoing_requests.tasks import reset_config

    settings.LOG_OUTGOING_REQUESTS_DB_SAVE = False
    config = OutgoingRequestsLogConfig.get_solo()
    assert isinstance(config, OutgoingRequestsLogConfig)
    config.save_to_db = "yes"
    config.save()
    qs = OutgoingRequestsLog.objects.all()
    requests_mock.get("https://example.com", status_code=200)

    requests.get("https://example.com")
    assert qs.count() == 1

    reset_config()

    requests.get("https://example.com")
    assert qs.count() == 1


@pytest.mark.django_db
def test_saving_config_schedules_config_reset(mocker):
    config = OutgoingRequestsLogConfig.get_solo()
    assert isinstance(config, OutgoingRequestsLogConfig)
    config.save_to_db = "yes"
    mock_schedule = mocker.patch("log_outgoing_requests.models.schedule_config_reset")
    config.save()
    mock_schedule.assert_called_once()


@pytest.mark.skipif(not has_celery, reason="Celery is optional dependency")
def test_schedule_config_schedules_celery_task(settings, mocker):
    mock_task = mocker.patch(
        "log_outgoing_requests.config_reset.reset_config.apply_async"
    )
    settings.LOG_OUTGOING_REQUESTS_RESET_DB_SAVE_AFTER = 1
    schedule_config_reset()
    mock_task.assert_called_once_with(countdown=60)
