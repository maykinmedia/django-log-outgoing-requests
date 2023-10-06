import logging
from datetime import timedelta
from typing import Union
from urllib.parse import urlparse

from django.core.validators import MinValueValidator
from django.db import models
from django.utils import timezone
from django.utils.functional import cached_property
from django.utils.translation import gettext_lazy as _

from solo.models import SingletonModel  # type: ignore

from .conf import settings
from .config_reset import schedule_config_reset
from .constants import SaveLogsChoice

logger = logging.getLogger(__name__)


class OutgoingRequestsLogQueryset(models.QuerySet):
    def prune(self) -> int:
        max_age = settings.LOG_OUTGOING_REQUESTS_MAX_AGE
        if max_age is None:
            return 0

        now = timezone.now()
        num_deleted, _ = self.filter(timestamp__lt=now - timedelta(max_age)).delete()
        return num_deleted


class OutgoingRequestsLog(models.Model):
    url = models.TextField(
        verbose_name=_("URL"),
        help_text=_("The url of the outgoing request."),
    )

    # hostname is added so we can filter on it in the admin page
    hostname = models.CharField(
        verbose_name=_("Hostname"),
        max_length=255,
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

    # Request content
    req_content_type = models.CharField(
        verbose_name=_("Request content type"),
        max_length=50,
        help_text=_("The content type of the request."),
    )
    req_headers = models.TextField(
        verbose_name=_("Request headers"), help_text=_("The request headers.")
    )
    req_body_encoding = models.CharField(
        _("Request encoding"),
        max_length=24,
        blank=True,
        help_text=_(
            "The encoding is either extracted from the Content-Type header or, if "
            "absent, taken from the default encoding configured for the content type. "
            "If the decoded request content is not displaying correctly, you may try "
            "changing the encoding value here."
        ),
    )
    req_body = models.BinaryField(
        verbose_name=_("Request body"), default=b"", help_text=_("The request body.")
    )

    # Response content
    res_content_type = models.CharField(
        verbose_name=_("Response content type"),
        max_length=50,
        help_text=_("The content type of the response."),
    )
    res_headers = models.TextField(
        verbose_name=_("Response headers"), help_text=_("The response headers.")
    )
    res_body = models.BinaryField(
        verbose_name=_("Response body"), default=b"", help_text=_("The response body.")
    )
    res_body_encoding = models.CharField(
        _("Response encoding"),
        max_length=24,
        blank=True,
        help_text=_(
            "The encoding is either extracted from the Content-Type header or, if "
            "absent, taken from the default encoding configured for the content type. "
            "If the decoded response content is not displaying correctly, you may try "
            "changing the encoding value here."
        ),
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
        help_text=_("Text providing information in case of request failure."),
    )

    objects = OutgoingRequestsLogQueryset.as_manager()

    class Meta:
        verbose_name = _("Outgoing request log")
        verbose_name_plural = _("Outgoing request logs")

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

    request_body_decoded.short_description = _("Request body")  # type: ignore

    @cached_property
    def response_body_decoded(self) -> str:
        """
        Decoded response body for use in template.
        """
        return self._decode_body(self.res_body, self.res_body_encoding)

    response_body_decoded.short_description = _("Response body")  # type: ignore


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

    class Meta:
        verbose_name = _("Outgoing request log configuration")

    def save(self, *args, **kwargs):
        super().save(*args, **kwargs)
        schedule_config_reset()

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
