=========
Structlog
=========

Django-log-outgoing-requests is structlog friendly and ships a built-in processor for
request/response metadata *and* bodies.

Log events
==========

The library emits two kinds of log events, with a format that's structlog-friendly:

``outgoing_request_response_received``
    Emitted whenever a successful request-response cycle is completed.

    .. note:: When requests follows redirects, this leads to a log event for each
       request-response cycle in the redirect chain being logged.

``outgoing_request_errored``
    Emitted whenever an outgoing request failed. Usually there's no response information
    available.


Processors
==========

Log-outgoing-requests includes a built-in structlog processor that extracts the
request and response details and adds them to the event dict. Typically, you'll want
to include this in your loggers foreign pre chain, for example:

.. code-block:: python
    :linenos:
    :emphasize-lines: 16,28

    LOGGING = {
        "version": 1,
        "disable_existing_loggers": False,
        "formatters": {
            # structlog - foreign_pre_chain handles logs coming from stdlib logging module,
            # while the `structlog.configure` call handles everything coming from structlog.
            # They are mutually exclusive.
            "json": {
                "()": structlog.stdlib.ProcessorFormatter,
                "processor": structlog.processors.JSONRenderer(),
                "foreign_pre_chain": [
                    structlog.contextvars.merge_contextvars,
                    structlog.processors.TimeStamper(fmt="iso"),
                    structlog.stdlib.add_logger_name,
                    structlog.stdlib.add_log_level,
                    ExtractRequestAndResponseDetails(expand_headers=False),
                    structlog.stdlib.PositionalArgumentsFormatter(),
                ],
            },
            "plain_console": {
                "()": structlog.stdlib.ProcessorFormatter,
                "processor": structlog.dev.ConsoleRenderer(),
                "foreign_pre_chain": [
                    structlog.contextvars.merge_contextvars,
                    structlog.processors.TimeStamper(fmt="iso"),
                    structlog.stdlib.add_logger_name,
                    structlog.stdlib.add_log_level,
                    ExtractRequestAndResponseDetails(expand_headers=True),
                    structlog.stdlib.PositionalArgumentsFormatter(),
                ],
            },
        },
        ...
    }

**API reference**

.. autoclass:: log_outgoing_requests.structlog.ExtractRequestAndResponseDetails
