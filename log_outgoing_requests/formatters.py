import logging
import textwrap
from typing import Union, cast

from requests import RequestException
from requests.models import PreparedRequest, Response

from .compat import format_exception
from .typing import RequestLogRecord, is_request_log_record


def format_headers(headers) -> str:
    return "\n".join(f"{k}: {v}" for k, v in headers.items())


def format_body(content: Union[str, bytes, None], prefix: str) -> str:
    from .conf import settings

    if settings.LOG_OUTGOING_REQUESTS_EMIT_BODY:
        return f"\n{prefix} body:\n{content}"
    return ""


def format_request(req: PreparedRequest) -> str:
    template = textwrap.dedent(
        """
        ---------------- request ----------------
        {req.method} {req.url}
        {reqhdrs} {request_body}
    """
    )
    return template.format(
        req=req,
        reqhdrs=format_headers(req.headers),
        request_body=format_body(req.body, "Request"),
    )


def format_response(resp: Response):
    template = textwrap.dedent(
        """
        ---------------- response ----------------
        {resp.status_code} {resp.reason} {resp.url}
        {reshdrs} {response_body}

    """
    )
    return template.format(
        resp=resp,
        reshdrs=format_headers(resp.headers),
        response_body=format_body(resp.content, "Response"),
    )


def format_error(exception: RequestException) -> str:
    template = textwrap.dedent(
        """
        ---------------- error ----------------
        {msg}

        {tb}
    """
    )
    tb = "\n".join(format_exception(exception))
    output = template.format(msg=str(exception), tb=tb)
    if (request := exception.request) is None:
        return output

    # we have request information, let's include it
    formatted_request = format_request(request)
    return f"{formatted_request}\n{output}"


class HttpFormatter(logging.Formatter):
    """
    Display request and response (meta) details of python requests library log records.

    Depending on the configuration, either only the metadata or metadata + body of
    requests and matching responses is emitted.

    Metadata:

        * HTTP method
        * Request URL
        * Request headers (masking auth details)
        * Response status
        * Response reason
        * Response headers
    """

    def _formatMessageWithResponse(self, record: RequestLogRecord) -> str:
        assert record.req is not None
        assert record.res is not None
        return "{request}\n{response}".format(
            request=format_request(record.req),
            response=format_response(record.res),
        )

    def formatMessage(self, record):
        result = super().formatMessage(record)
        if not is_request_log_record(record):
            return result

        # if there is a response, apply the happy-flow formatting
        if getattr(record, "res", None) is not None:
            record = cast(RequestLogRecord, record)
            output = self._formatMessageWithResponse(record)
            return f"{result}{output}"

        # if there is exception information, extract the details from that
        if record.exc_info and isinstance(
            (exception := record.exc_info[1]), RequestException
        ):
            output = format_error(exception)
            return f"{result}{output}"

        # any other log record - use the default formatter
        return result
