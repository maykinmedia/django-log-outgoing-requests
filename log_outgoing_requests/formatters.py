import logging
import textwrap

from django.conf import settings


class HttpFormatter(logging.Formatter):
    def _formatHeaders(self, d):
        return "\n".join(f"{k}: {v}" for k, v in d.items())

    def _formatBody(self, content: str, request_or_response: str) -> str:
        if settings.LOG_OUTGOING_REQUESTS_EMIT_BODY:
            return f"\n{request_or_response} body:\n{content}"
        return ""

    def formatMessage(self, record):
        result = super().formatMessage(record)

        if record.name != "requests":
            return result

        result += textwrap.dedent(
            """
            ---------------- request ----------------
            {req.method} {req.url}
            {reqhdrs} {request_body}

            ---------------- response ----------------
            {res.status_code} {res.reason} {res.url}
            {reshdrs} {response_body}

        """
        ).format(
            req=record.req,
            res=record.res,
            reqhdrs=self._formatHeaders(record.req.headers),
            reshdrs=self._formatHeaders(record.res.headers),
            request_body=self._formatBody(record.req.body, "Request"),
            response_body=self._formatBody(record.res.content, "Response"),
        )

        return result
