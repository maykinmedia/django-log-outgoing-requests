from django.utils.safestring import SafeString

import pytest

from log_outgoing_requests.syntax_highlighting import highlight_body


@pytest.mark.parametrize(
    "body,content_type",
    [
        (
            '{"foo":"bar"}',
            "application/json",
        ),
        (
            '{"foo":"bar"}',
            "application/hal+json",
        ),
        (
            '{"foo":"bar"}',
            "application/problem+json",
        ),
        (
            "<root><child /></root>",
            "text/xml",
        ),
        (
            "<root><child /></root>",
            "application/xml",
        ),
        (
            "foo\nbar",
            "text/plain",
        ),
        (
            "<html><head></head><body></body></html>",
            "text/html",
        ),
    ],
)
def test_valid_well_formed_bodies(body: str, content_type: str):
    result = highlight_body(body, content_type)

    assert result
    assert isinstance(result, SafeString)
    assert "\n" in result


@pytest.mark.parametrize(
    "body,content_type",
    [
        (
            '{"foo":"bar"}',
            "",
        ),
        (
            "<html><head></head><body></body></html>",
            "invalid",
        ),
    ],
)
def test_passthrough_unknown_content_type(body: str, content_type: str):
    result = highlight_body(body, content_type)

    assert result == body


@pytest.mark.parametrize(
    "body,content_type",
    [
        (
            '{"foo":}',
            "application/json",
        ),
        (
            '{"foo":}',
            "application/problem+json",
        ),
        (
            "<root><child />",
            "text/xml",
        ),
        (
            "<root><child />",
            "application/soap+xml",
        ),
    ],
)
def test_is_resilient_against_malformed_bodies(body: str, content_type: str):
    result = highlight_body(body, content_type)

    assert result == body or isinstance(result, SafeString)


def test_is_resilient_against_unknown_content_types():
    result = highlight_body("foo", "31bf369b-0ace-4028-aeec-c639c01bd4ef")

    assert result == "foo"


def test_handles_empty_bodies():
    result = highlight_body("", "text/plain")

    assert result == "-"
