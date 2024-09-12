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


@pytest.mark.django_db
def test_list_url_is_trucated_over_200_chars(admin_client):
    OutgoingRequestsLog.objects.create(
        id=1,
        url="https://example.com/a1b2c3d4e5f6g7h8i9j0k1l2m3n4o5p6q7r8s9t1u2v3w4x5y6z1a2b3c4d5e6f7g8h9i0j1k2l3m4n5o6p7q8r9s1t2u3v4w5x6y7z/some-path-3894ndjidjd93djjd3eu9jjddu9eu93j3e39ei9idjd3ddksdj9393/some-path/some-path-as-well/skdlkdlskdksdkd9828393jdd",
        timestamp=timezone.now(),
    )
    url = reverse("admin:log_outgoing_requests_outgoingrequestslog_changelist")

    response = admin_client.get(url)
    html = response.content.decode("utf-8")
    doc = PyQuery(html)
    truncated_url = doc.find(".field-truncated_url").text()

    assert (
        truncated_url
        == "/a1b2c3d4e5f6g7h8i9j0k1l2m3n4o5p6q7r8s9t1u2v3w4x5y6z1a2b3c4d5e6f7g8h9i0j1k2l3m4n5o6p7q8r9s1t2u3v4w \u2026 d93djjd3eu9jjddu9eu93j3e39ei9idjd3ddksdj9393/some-path/some-path-as-well/skdlkdlskdksdkd9828393jdd"
    )


@pytest.mark.django_db
def test_list_url_is_not_trucated_under_200_chars(admin_client):
    OutgoingRequestsLog.objects.create(
        id=1,
        url="https://example.com/a1b2c3d4e/some-path",
        timestamp=timezone.now(),
    )
    url = reverse("admin:log_outgoing_requests_outgoingrequestslog_changelist")

    response = admin_client.get(url)
    html = response.content.decode("utf-8")
    doc = PyQuery(html)
    truncated_url = doc.find(".field-truncated_url").text()

    assert truncated_url == "/a1b2c3d4e/some-path"
