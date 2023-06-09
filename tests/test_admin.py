"""Tests for the admin interface"""

from django.urls import reverse
from django.utils import timezone

import pytest
import requests
from pyquery import PyQuery

from log_outgoing_requests.models import OutgoingRequestsLog, OutgoingRequestsLogConfig


#
# test display
#
@pytest.mark.django_db
def test_decoded_content_display(admin_client):
    """Assert that decoded request/response bodies are properly displayed"""

    log = OutgoingRequestsLog.objects.create(
        id=1,
        req_body=b"I'm a lumberjack and I'm okay.",
        res_body=b"I sleep all night and work all day.",
        timestamp=timezone.now(),
    )
    url = reverse(
        "admin:log_outgoing_requests_outgoingrequestslog_change", args=(log.pk,)
    )

    response = admin_client.get(url)
    assert response.status_code == 200

    html = response.content.decode("utf-8")
    doc = PyQuery(html)
    request_body = doc.find(".field-request_body .readonly").text()
    response_body = doc.find(".field-response_body .readonly").text()

    assert request_body == "I'm a lumberjack and I'm okay."
    assert response_body == "I sleep all night and work all day."


#
# test override of settings
#
@pytest.mark.django_db
def test_admin_override_db_save(requests_mock, request_mock_kwargs):
    """Assert that saving logs can be disabled in admin"""

    config = OutgoingRequestsLogConfig.get_solo()
    config.save_to_db = "no"
    config.save()

    requests_mock.get(**request_mock_kwargs)
    requests.get(
        request_mock_kwargs["url"], headers=request_mock_kwargs["request_headers"]
    )

    request_log = OutgoingRequestsLog.objects.last()

    assert request_log is None


@pytest.mark.django_db
def test_admin_override_save_body(requests_mock, request_mock_kwargs):
    """Assert that saving body can be disabled in admin"""

    config = OutgoingRequestsLogConfig.get_solo()
    config.save_body = "no"
    config.save()

    requests_mock.get(**request_mock_kwargs)
    requests.get(
        request_mock_kwargs["url"], headers=request_mock_kwargs["request_headers"]
    )

    request_log = OutgoingRequestsLog.objects.last()

    assert request_log.res_body == b""


@pytest.mark.django_db
def test_admin_override_max_content_length(requests_mock, request_mock_kwargs):
    """Assert that `max_content_length` can be overriden in admin"""

    config = OutgoingRequestsLogConfig.get_solo()
    config.max_content_length = "10"
    config.save()

    requests_mock.get(**request_mock_kwargs)
    requests.get(
        request_mock_kwargs["url"], headers=request_mock_kwargs["request_headers"]
    )

    request_log = OutgoingRequestsLog.objects.last()

    assert request_log.res_body == b""
