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
    if not content_type:
        return body

    try:
        lexer = get_lexer_for_mimetype(content_type)
    except ClassNotFound:
        return body

    result = highlight(body, lexer, _FORMATTER)
    return mark_safe(result)


if __name__ == "__main__":  # pragma: no cover
    from pathlib import Path

    PACKAGE_ROOT = Path(__file__).parent.resolve()
    outfile = (
        PACKAGE_ROOT / "static" / "log_outgoing_requests" / "css" / "highlight.css"
    )
    output_css = _FORMATTER.get_style_defs()
    outfile.write_text(output_css)
