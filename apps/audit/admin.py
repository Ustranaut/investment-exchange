from django.contrib import admin
from .models import AuditLog


@admin.register(AuditLog)
class AuditLogAdmin(admin.ModelAdmin):
    list_display = ("created_at", "actor", "entity_type", "object_id", "action")
    list_filter = ("action", "entity_type", "created_at")
    search_fields = ("actor__email", "entity_type", "object_id")
    readonly_fields = (
        "actor", "entity_type", "object_id", "action",
        "before_data", "after_data", "created_at",
    )

    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False
