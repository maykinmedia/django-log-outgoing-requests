"""Tests for the utility functions"""

import logging
from typing import Iterable, Tuple, Union

from requests import PreparedRequest, Response

from .compat import parse_header_parameters
from .conf import settings
from .datastructures import ContentType, ProcessedBody
from .models import OutgoingRequestsLogConfig

logger = logging.getLogger(__name__)

HttpObj = Union[PreparedRequest, Response]


def process_body(http_obj: HttpObj, config: OutgoingRequestsLogConfig) -> ProcessedBody:
    """
    Process a request or response body by parsing the meta information.
    """
    content_type, encoding = parse_content_type_header(http_obj)
    if not encoding:
        encoding = get_default_encoding(content_type)
    allow_persisting = check_content_type(content_type) and check_content_length(
        http_obj, config=config
    )
    content = _get_body(http_obj) if allow_persisting else b""
    return ProcessedBody(
        allow_saving_to_db=allow_persisting,
        content=content or b"",
        content_type=content_type,
        encoding=encoding,
    )


#
# Handler utilities
#
def _get_body(http_obj: HttpObj) -> Union[bytes, str, None]:
    return http_obj.content if isinstance(http_obj, Response) else http_obj.body


def _get_content_length(http_obj: HttpObj) -> str:
    """
    Try to determine the size of a request/response content.

    Try `Content-Length` header first. If not present, try to
    determine the size by reading `len(body)`. The entire content
    is thereby read into memory (the assumption being that the content
    will eventually be consumed anyway).
    """
    content_length = http_obj.headers.get("Content-Length", "")

    if not content_length:
        body = _get_body(http_obj)
        if body is not None:
            content_length = str(len(body))

    return content_length


def check_content_length(
    http_obj: HttpObj,
    config: "OutgoingRequestsLogConfig",
) -> bool:
    """
    Check `content_length` against settings.

    If `content_length` could not be determined (i.e. `content_length` == ""), the test
    passes with a warning.
    """
    content_length = _get_content_length(http_obj)

    if not content_length:
        # for logging: get netloc (response) or url (request)
        target = getattr(http_obj, "netloc", "") or http_obj.url
        logger.warning(
            "Content length of the request/response (request netloc: %s) could not be determined."
            % target
        )
        return True

    max_content_length = config.max_content_length

    return int(content_length) <= max_content_length


def parse_content_type_header(http_obj: HttpObj) -> Tuple[str, str]:
    """
    Wrapper around Django's `parse_header`.

    If a charset/encoding is found, we replace the representation of it with a string.

    :returns: a `tuple` (content_type, encoding)
    """
    content_type_line = http_obj.headers.get("Content-Type", "")
    if not content_type_line:
        return ("", "")

    content_type, params = parse_header_parameters(content_type_line)
    encoding = params.get("charset", "")
    return content_type, encoding


def check_content_type(content_type: str) -> bool:
    """
    Check `content_type` against settings.

    The string patterns of the content types specified under `LOG_OUTGOING_REQUESTS_
    CONTENT_TYPES` are split into two groups. For regular patterns not containing a
    wildcard ("text/xml"), check if `content_type.pattern` is included in the list.
    For patterns containing a wildcard ("text/*"), check if `content_type.pattern`
    is a substring of any pattern contained in the list.
    """
    allowed_content_types: Iterable[
        ContentType
    ] = settings.LOG_OUTGOING_REQUESTS_CONTENT_TYPES
    regular_patterns = [
        item.pattern for item in allowed_content_types if not item.pattern.endswith("*")
    ]
    wildcard_patterns = [
        item.pattern for item in allowed_content_types if item.pattern.endswith("*")
    ]

    if content_type in regular_patterns:
        return True

    return any(content_type.startswith(pattern[:-1]) for pattern in wildcard_patterns)


def get_default_encoding(content_type_pattern: str) -> str:
    """
    Get the default encoding for the `ContentType` with the associated pattern.
    """
    allowed_content_types: Iterable[
        ContentType
    ] = settings.LOG_OUTGOING_REQUESTS_CONTENT_TYPES

    regular_types = [
        item for item in allowed_content_types if not item.pattern.endswith("*")
    ]
    wildcard_types = [
        item for item in allowed_content_types if item.pattern.endswith("*")
    ]

    content_type = next(
        (item for item in regular_types if item.pattern == content_type_pattern), None
    )
    if content_type is None:
        content_type = next(
            (
                item
                for item in wildcard_types
                if content_type_pattern.startswith(item.pattern[:-1])
            ),
            None,
        )

    return content_type.default_encoding if content_type else ""
