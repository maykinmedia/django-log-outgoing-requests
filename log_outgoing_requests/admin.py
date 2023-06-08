from django import forms
from django.contrib import admin
from django.utils.translation import gettext as _

from solo.admin import SingletonModelAdmin

from .conf import settings
from .models import OutgoingRequestsLog, OutgoingRequestsLogConfig


@admin.register(OutgoingRequestsLog)
class OutgoingRequestsLogAdmin(admin.ModelAdmin):
    fields = (
        "url",
        "hostname",
        "query_params",
        "params",
        "status_code",
        "method",
        "response_ms",
        "timestamp",
        "req_content_type",
        "res_content_type",
        "req_headers",
        "res_headers",
        "trace",
    )
    readonly_fields = fields
    list_display = (
        "hostname",
        "url",
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
    change_form_template = "log_outgoing_requests/change_form.html"

    class Media:
        css = {
            "all": ("log_outgoing_requests/css/admin.css",),
        }

    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False

    @admin.display(description=_("Query parameters"))
    def query_params(self, obj):
        return obj.query_params


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
