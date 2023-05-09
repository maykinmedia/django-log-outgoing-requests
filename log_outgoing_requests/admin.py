from django.contrib import admin
from django.utils.translation import gettext as _

from solo.admin import SingletonModelAdmin

from .models import OutgoingRequestsLog, OutgoingRequestsLogConfig


@admin.display(description="Response body")
def response_body(obj):
    return f"{obj}".upper()


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
        "req_body",
        "res_body",
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
    list_filter = ("method", "status_code", "hostname", "timestamp")
    search_fields = ("url", "params", "hostname")
    date_hierarchy = "timestamp"
    show_full_result_count = False

    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False

    def query_params(self, obj):
        return obj.query_params

    query_params.short_description = _("Query parameters")

    class Media:
        css = {
            "all": ("log_outgoing_requests/css/admin.css",),
        }


@admin.register(OutgoingRequestsLogConfig)
class OutgoingRequestsLogConfigAdmin(SingletonModelAdmin):
    fields = (
        "save_to_db",
        "save_body",
    )
    list_display = (
        "save_to_db",
        "save_body",
    )
