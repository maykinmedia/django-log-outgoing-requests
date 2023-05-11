from django import forms
from django.conf import settings
from django.contrib import admin
from django.shortcuts import get_object_or_404
from django.utils.translation import gettext as _

from solo.admin import SingletonModelAdmin  # type: ignore

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

    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False

    def query_params(self, obj):
        return obj.query_params

    def change_view(self, request, object_id, extra_context=None):
        """
        Add log object to to context for use in template.
        """
        log = get_object_or_404(OutgoingRequestsLog, id=object_id)

        extra_context = extra_context or {}
        extra_context["log"] = log

        return super().change_view(request, object_id, extra_context=extra_context)

    query_params.short_description = _("Query parameters")  # type: ignore

    class Media:
        css = {
            "all": ("log_outgoing_requests/css/admin.css",),
        }


class ConfigAdminForm(forms.ModelForm):
    class Meta:
        model = OutgoingRequestsLogConfig
        fields = "__all__"
        widgets = {"allowed_content_types": forms.CheckboxSelectMultiple}
        help_texts = {
            "save_to_db": _(
                "Whether request logs should be saved to the database (default: {default})."
            ).format(default=settings.LOG_OUTGOING_REQUESTS_DB_SAVE),
            "save_body": _(
                "Wheter the body of the request and response should be logged (default: "
                "{default})."
            ).format(default=settings.LOG_OUTGOING_REQUESTS_DB_SAVE_BODY),
        }


@admin.register(OutgoingRequestsLogConfig)
class OutgoingRequestsLogConfigAdmin(SingletonModelAdmin):
    form = ConfigAdminForm
