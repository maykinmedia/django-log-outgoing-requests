import pytest
import requests

from log_outgoing_requests.config_reset import schedule_config_reset
from log_outgoing_requests.models import OutgoingRequestsLog, OutgoingRequestsLogConfig

try:
    import celery
except ImportError:
    celery = None

has_celery = celery is not None


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
