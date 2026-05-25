from .models import AuditLog


def log_action(
    *,
    user=None,
    action_type,
    status=AuditLog.STATUS_INFO,
    module=None,
    submodule=None,
    related_object="",
    file_or_report="",
    error_message="",
    metadata=None,
):
    return AuditLog.objects.create(
        user=user if getattr(user, "is_authenticated", False) else None,
        action_type=action_type,
        status=status,
        module=module,
        submodule=submodule,
        related_object=related_object,
        file_or_report=file_or_report,
        error_message=error_message,
        metadata=metadata or {},
    )
