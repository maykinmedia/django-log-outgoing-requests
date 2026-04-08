import json
from collections.abc import Callable, Mapping

from django.http.request import MediaType
from django.utils.safestring import mark_safe

from pygments import highlight
from pygments.formatters import HtmlFormatter
from pygments.lexers import get_lexer_for_mimetype
from pygments.util import ClassNotFound

_FORMATTER = HtmlFormatter(
    noclasses=False,  # no inline styles
    nowrap=False,
    cssclass="lor-http-body",
    style="monokai",
)


CONTENT_TYPE_TO_FORMATTER: Mapping[str, Callable[[str], str]] = {
    "json": lambda body: json.dumps(json.loads(body), indent=2),
    "xml": lambda body: body,
    "noop": lambda body: body,
}


def format_body(body: str, content_type: str) -> str:
    """
    Given the content type, prettify the body content.
    """
    assert body, "Can't operate on empty body"
    assert content_type, "Needs content-type information"
    if "json" in content_type:
        formatter = CONTENT_TYPE_TO_FORMATTER["json"]
    elif "xml" in content_type:
        formatter = CONTENT_TYPE_TO_FORMATTER["xml"]
    else:
        formatter = CONTENT_TYPE_TO_FORMATTER["noop"]
    return formatter(body)


def highlight_body(body: str, content_type: str) -> str:
    """
    Highlight the body, best effort.

    If there is no body, content type or no lexer can be found for the provided content
    type, the body is returned as-is, without highlighting.

    :param body: The body to highlight.
    :param content_type: The content type of the body, used as input to select the
      highlighter. It must already have stripped off the encoding parameter, if present.
    """
    if not body:
        return "-"

    # normalize the content type
    # https://datatracker.ietf.org/doc/html/rfc6838#section-4.2.8 specifies the
    # structured syntax name suffix, necessary to process content types like soap+xml /
    # hal+json / problem+json etc...
    media_type = MediaType(content_type)
    if "+" in media_type.sub_type:
        normalized_sub_type = media_type.sub_type.rsplit("+")[1]
        content_type = f"{media_type.main_type}/{normalized_sub_type}"

    if not content_type:
        return body

    try:
        lexer = get_lexer_for_mimetype(content_type)
    except ClassNotFound:
        return body

    formatted_body = format_body(body, content_type)
    result = highlight(formatted_body, lexer, _FORMATTER)
    return mark_safe(result)


if __name__ == "__main__":  # pragma: no cover
    from pathlib import Path

    PACKAGE_ROOT = Path(__file__).parent.resolve()
    outfile = (
        PACKAGE_ROOT / "static" / "log_outgoing_requests" / "css" / "highlight.css"
    )
    output_css = _FORMATTER.get_style_defs()
    outfile.write_text(output_css)
