from urllib.parse import urlparse

from django import forms
from django.contrib import admin
from django.utils.translation import gettext as _

from solo.admin import SingletonModelAdmin

from .conf import settings
from .models import OutgoingRequestsLog, OutgoingRequestsLogConfig


@admin.register(OutgoingRequestsLog)
class OutgoingRequestsLogAdmin(admin.ModelAdmin):
    list_display = (
        "hostname",
        "truncated_url",
        "params",
        "status_code",
        "method",
        "response_ms",
        "timestamp",
    )
    list_filter = ("method", "timestamp", "status_code", "hostname")
    search_fields = ("url", "params", "hostname")
    date_hierarchy = "timestamp"
    show_full_result_count = False

    fieldsets = (
        (
            _("Request"),
            {
                "fields": (
                    "method",
                    "url",
                    "timestamp",
                    "query_params",
                    "params",
                    "req_headers",
                    "req_content_type",
                    "req_body_encoding",
                    "request_body",
                )
            },
        ),
        (
            _("Response"),
            {
                "fields": (
                    "status_code",
                    "response_ms",
                    "res_headers",
                    "res_content_type",
                    "res_body_encoding",
                    "response_body",
                )
            },
        ),
        (_("Extra"), {"fields": ("trace",)}),
    )
    readonly_fields = (
        "url",
        "timestamp",
        "method",
        "query_params",
        "params",
        "req_headers",
        "req_content_type",
        "request_body",
        "status_code",
        "response_ms",
        "res_headers",
        "res_content_type",
        "response_body",
        "trace",
    )

    class Media:
        css = {
            "all": ("log_outgoing_requests/css/admin.css",),
        }

    def has_add_permission(self, request):
        return False

    @admin.display(description=_("Query parameters"))
    def query_params(self, obj):
        return obj.query_params

    @admin.display(description=_("Request body"))
    def request_body(self, obj) -> str:
        return obj.request_body_decoded or "-"

    @admin.display(description=_("Response body"))
    def response_body(self, obj) -> str:
        return obj.response_body_decoded or "-"

    def truncated_url(self, obj):
        parsed_url = urlparse(obj.url)
        path = parsed_url.path
        max_length = 200
        path_length = len(path)

        if path_length <= max_length:
            return path

        half_length = (max_length - 3) // 2
        left_half = path[:half_length]
        right_half = path[-half_length:]
        return left_half + " \u2026 " + right_half


class ConfigAdminForm(forms.ModelForm):
    class Meta:
        model = OutgoingRequestsLogConfig
        fields = "__all__"
        help_texts = {
            "save_to_db": _(
                "Whether request logs should be saved to the database (default: {default})."
            ).format(default=settings.LOG_OUTGOING_REQUESTS_DB_SAVE),
            "save_body": _(
                "Whether the body of the request and response should be logged (default: "
                "{default})."
            ).format(default=settings.LOG_OUTGOING_REQUESTS_DB_SAVE_BODY),
        }


@admin.register(OutgoingRequestsLogConfig)
class OutgoingRequestsLogConfigAdmin(SingletonModelAdmin):
    form = ConfigAdminForm
