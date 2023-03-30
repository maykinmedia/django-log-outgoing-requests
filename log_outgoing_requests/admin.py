from django.contrib import admin
from django.utils.translation import gettext as _

from .models import OutgoingRequestsLog


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
    list_filter = ("method", "status_code", "hostname")
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
