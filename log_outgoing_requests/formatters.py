import logging
import textwrap


class HttpFormatter(logging.Formatter):
    def _formatHeaders(self, d):
        return "\n".join(f"{k}: {v}" for k, v in d.items())

    def formatMessage(self, record):
        result = super().formatMessage(record)
        if record.name == "requests":
            result += textwrap.dedent(
                """
                ---------------- request ----------------
                {req.method} {req.url}
                {reqhdrs}

                ---------------- response ----------------
                {res.status_code} {res.reason} {res.url}
                {reshdrs}

            """
            ).format(
                req=record.req,
                res=record.res,
                reqhdrs=self._formatHeaders(record.req.headers),
                reshdrs=self._formatHeaders(record.res.headers),
            )

        return result
