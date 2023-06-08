import logging
from typing import Union
from urllib.parse import urlparse

from django.core.validators import MinValueValidator
from django.db import models
from django.utils.functional import cached_property
from django.utils.translation import gettext_lazy as _

from solo.models import SingletonModel  # type: ignore

from .conf import settings
from .constants import SaveLogsChoice

logger = logging.getLogger(__name__)


class OutgoingRequestsLog(models.Model):
    url = models.URLField(
        verbose_name=_("URL"),
        max_length=1000,
        default="",
        help_text=_("The url of the outgoing request."),
    )

    # hostname is added so we can filter on it in the admin page
    hostname = models.CharField(
        verbose_name=_("Hostname"),
        max_length=255,
        default="",
        help_text=_("The netloc/hostname part of the url."),
    )
    params = models.TextField(
        verbose_name=_("Parameters"),
        blank=True,
        help_text=_("The parameters (if they exist)."),
    )
    status_code = models.PositiveIntegerField(
        verbose_name=_("Status code"),
        null=True,
        blank=True,
        help_text=_("The status code of the response."),
    )
    method = models.CharField(
        verbose_name=_("Method"),
        max_length=10,
        blank=True,
        help_text=_("The type of request method."),
    )
    req_content_type = models.CharField(
        verbose_name=_("Request content type"),
        max_length=50,
        default="",
        help_text=_("The content type of the request."),
    )
    res_content_type = models.CharField(
        verbose_name=_("Response content type"),
        max_length=50,
        default="",
        help_text=_("The content type of the response."),
    )
    req_headers = models.TextField(
        verbose_name=_("Request headers"),
        default="",
        help_text=_("The request headers."),
    )
    res_headers = models.TextField(
        verbose_name=_("Response headers"),
        default="",
        help_text=_("The response headers."),
    )
    req_body = models.BinaryField(
        verbose_name=_("Request body"),
        default=b"",
        help_text=_("The request body."),
    )
    res_body = models.BinaryField(
        verbose_name=_("Response body"),
        default=b"",
        help_text=_("The response body."),
    )
    req_body_encoding = models.CharField(
        max_length=24,
        default="",
    )
    res_body_encoding = models.CharField(
        max_length=24,
        default="",
    )
    response_ms = models.PositiveIntegerField(
        verbose_name=_("Response in ms"),
        default=0,
        help_text=_("This is the response time in ms."),
    )
    timestamp = models.DateTimeField(
        verbose_name=_("Timestamp"),
        help_text=_("This is the date and time the API call was made."),
    )
    trace = models.TextField(
        verbose_name=_("Trace"),
        default="",
        help_text=_("Text providing information in case of request failure."),
    )

    class Meta:
        verbose_name = _("Outgoing Requests Log")
        verbose_name_plural = _("Outgoing Requests Logs")

    def __str__(self):
        return ("{hostname} at {date}").format(
            hostname=self.hostname, date=self.timestamp
        )

    @cached_property
    def url_parsed(self):
        return urlparse(self.url)

    @property
    def query_params(self):
        return self.url_parsed.query

    def _decode_body(self, content: Union[bytes, memoryview], encoding: str) -> str:
        """
        Decode body for use in template.

        If the stored encoding is not found (either because it is empty or because of
        spelling errors etc.), we decode "blindly", replacing chars that could not be
        decoded.

        Inspired on :meth:`requests.models.Response.text`, which is Apache 2.0 licensed.
        """
        try:
            return str(content, encoding, errors="replace")
        except LookupError:
            # A LookupError is raised if the encoding was not found which could
            # indicate a misspelling or similar mistake.
            return str(content, errors="replace")

    @cached_property
    def request_body_decoded(self) -> str:
        """
        Decoded request body for use in template.
        """
        return self._decode_body(self.req_body, self.req_body_encoding)

    @cached_property
    def response_body_decoded(self) -> str:
        """
        Decoded response body for use in template.
        """
        return self._decode_body(self.res_body, self.res_body_encoding)


def get_default_max_content_length():
    """
    Get default value for max content length from settings.
    """
    return settings.LOG_OUTGOING_REQUESTS_MAX_CONTENT_LENGTH


class OutgoingRequestsLogConfig(SingletonModel):
    """Configuration options for request logging."""

    save_to_db = models.CharField(
        _("Save logs to database"),
        max_length=11,
        choices=SaveLogsChoice.choices,
        default=SaveLogsChoice.use_default,
    )
    save_body = models.CharField(
        _("Save request + response body"),
        max_length=11,
        choices=SaveLogsChoice.choices,
        default=SaveLogsChoice.use_default,
    )
    max_content_length = models.IntegerField(
        _("Maximal content size"),
        validators=[MinValueValidator(0)],
        default=get_default_max_content_length,
        help_text=_(
            "The maximal size of the request/response content (in bytes). "
            "If 'Require content length' is not checked, this setting has no effect."
        ),
    )

    @property
    def save_logs_enabled(self):
        """
        Use configuration option or settings to determine if logs should be saved.
        """
        if self.save_to_db == SaveLogsChoice.use_default:
            return settings.LOG_OUTGOING_REQUESTS_DB_SAVE
        return self.save_to_db == SaveLogsChoice.yes

    @property
    def save_body_enabled(self):
        """
        Use configuration option or settings to determine if log bodies should be saved.
        """
        if self.save_body == SaveLogsChoice.use_default:
            return settings.LOG_OUTGOING_REQUESTS_DB_SAVE_BODY
        return self.save_body == SaveLogsChoice.yes

    class Meta:
        verbose_name = _("Outgoing Requests Log Configuration")
