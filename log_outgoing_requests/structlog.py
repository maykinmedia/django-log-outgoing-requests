"""
Implement support for optional structlog integration.
"""

from collections.abc import Mapping
from typing import Any, Literal, assert_never
from urllib.parse import urlparse

from django.views.debug import SafeExceptionReporterFilter

from requests.models import CaseInsensitiveDict, PreparedRequest, Response

from .typing import (
    EventDict,
    is_any_request_log_record,
    is_error_request_log_record,
    is_request_log_record,
)

type WrappedLogger = Any


class ExtractRequestAndResponseDetails:
    """
    Structlog processor that can extract request and response details from log records.

    Use this processor in your foreign pre-chain configuration to extract request,
    response and error details from outgoing request logs.

    :param expand_headers: Boolean that controls whether the request and response
      headers are added as a container or individual (prefixed) keys to the event dict.
      For the JSON renderer, you typically want to leave this disabled, while for the
      console renderer (logfmt) you'll probably want to set it to ``True``.
    :param extract_bodies: If enabled, request and response bodies smaller than the
      treshold (see :attr:`body_max_content_length`) are added to the event dict as
      well. Additionally, the ``LOG_OUTGOING_REQUESTS_CONTENT_TYPES`` setting is
      checked for an allow-list of content types to log. Be careful when you enable
      this, as it can quickly explode your log storage.

      Note that bodies from streaming responses (e.g.
      ``requests.get(url, stream=True)``) are never extracted.
    :param body_max_content_length: If body extraction is enabled, this parameter
      controls the maximum size of bodies to be logged. Bodies that are larger will not
      be added to the event dict.
    """

    def __init__(
        self,
        expand_headers: bool = False,
        extract_bodies: bool = False,
        body_max_content_length: int = 10_240,  # 10kB
    ):

        self.expand_headers = expand_headers
        self.extract_bodies = extract_bodies
        self.body_max_content_length = body_max_content_length

    def __call__(self, _: WrappedLogger, __: str, event_dict: EventDict):
        record = event_dict.get("_record")
        if record is None or not is_any_request_log_record(record):
            return event_dict

        if is_error_request_log_record(record):
            request = record.request_exception.request
            response = record.request_exception.response
        elif is_request_log_record(record):
            request = record.req
            response = record.res
        else:  # pragma: no cover
            assert_never(record)

        if request is None:  # nothing to do, no information...
            return event_dict

        assert isinstance(request, PreparedRequest)

        parsed_url = urlparse(request.url)
        event_dict.update(
            {
                "url": request.url,
                "method": request.method,
                "hostname": parsed_url.netloc,
                "query": parsed_url.query,
                **self._process_headers(request.headers, "req"),
            }
        )
        self._add_body_details(event_dict, request)

        if response is not None:
            event_dict.update(
                {
                    "status_code": response.status_code,
                    "response_ms": int(response.elapsed.total_seconds() * 1000),
                    **self._process_headers(response.headers, "resp"),
                }
            )
            self._add_body_details(event_dict, response, is_stream=record.stream)

        return event_dict

    def _process_headers(
        self,
        headers: CaseInsensitiveDict,
        direction: Literal["req", "resp"],
    ) -> Mapping[str, Mapping[str, str]] | Mapping[str, str]:
        _normalized_headers: Mapping[str, str] = dict(headers)

        # obfuscate potential sensitive headers
        if direction == "req":
            filter = SafeExceptionReporterFilter()
            _normalized_headers = {
                key: filter.cleanse_setting(key, value)
                for key, value in _normalized_headers.items()
            }

        if not self.expand_headers:
            return {f"{direction}_headers": _normalized_headers}
        return {
            f"{direction}_header_{name.lower().replace('-', '_')}": value
            for name, value in _normalized_headers.items()
        }

    def _add_body_details(
        self,
        event_dict: EventDict,
        http_obj: PreparedRequest | Response,
        is_stream: bool = False,
    ) -> None:
        from .models import OutgoingRequestsLogConfig
        from .utils import process_body

        if not self.extract_bodies:
            return

        direction: Literal["req", "resp"] = (
            "resp" if isinstance(http_obj, Response) else "req"
        )

        config = OutgoingRequestsLogConfig(
            max_content_length=self.body_max_content_length
        )
        body_details = process_body(http_obj, config, is_stream=is_stream)
        event_dict.update(
            {
                f"{direction}_content_type": body_details.content_type,
                f"{direction}_encoding": body_details.encoding,
            }
        )
        if content := body_details.content:
            event_dict[f"{direction}_body"] = content

        if is_stream:
            event_dict[f"{direction}_body_streaming"] = True
