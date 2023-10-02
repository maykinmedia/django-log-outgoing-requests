from django.conf import settings

from appconf import AppConf

from .datastructures import ContentType

__all__ = ["settings"]


class LogOutgoingRequestsConf(AppConf):
    """
    Settings for django-log-outgoing-requests.

    To override a setting, prefix it with ``LOG_OUTGOING_REQUESTS_`` in your own
    settings file.
    """

    DB_SAVE = False
    """
    Whether request logs should be saved to the database.

    This can be overridden at runtime via configuration in the admin.
    """
    DB_SAVE_BODY = False
    """
    Whether request/response bodies should be saved to the database.

    This can be overridden at runtime via configuration in the admin.
    """
    CONTENT_TYPES = [
        ContentType(pattern="application/json", default_encoding="utf-8"),
        ContentType(pattern="application/soap+xml", default_encoding="utf-8"),
        ContentType(pattern="application/xml", default_encoding="utf-8"),
        ContentType(pattern="text/xml", default_encoding="iso-8859-1"),
        ContentType(pattern="text/*", default_encoding="utf-8"),
    ]
    """
    Allowlist of content types for which the body may be saved to the database.

    Use :class:`log_outgoing_requests.datastructures.ContentType` to configure this
    setting.
    """
    EMIT_BODY = False
    """
    Whether request/response body may be emitted in the logs.
    """
    MAX_CONTENT_LENGTH = 524_288  # 0.5 MB
    """
    The maximum size of request/response bodies for saving to the database, in bytes.

    If the body is larger than this treshold, the log record will still be saved to the
    database, but the body will be missing.
    """

    MAX_AGE = 1
    """
    The maximum age (in days) of request logs, after which they are deleted (via a Celery
    task, Django management command, or the like).
    """

    RESET_DB_SAVE_AFTER = 60
    """
    If the config has been updated, reset the database logging after the specified
    number of minutes.

    To protect against unintended logging of potentially sensitive data after debugging,
    this helps in resetting the "save to DB" configuration option. It resets back to
    "use the default from settings".

    If the value is falsy (including zero), then no reset takes place at all.

    .. note:: this requires Celery to be installed, an optional dependency.
    """
