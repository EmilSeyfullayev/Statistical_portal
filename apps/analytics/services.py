from .models import InteractionEvent


def request_metadata(request):
    return {
        "ip": request.META.get("REMOTE_ADDR", ""),
        "user_agent": request.META.get("HTTP_USER_AGENT", "")[:300],
        "method": request.method,
    }


def record_interaction(
    request,
    event_type,
    *,
    module=None,
    submodule=None,
    dashboard=None,
    report=None,
    target_url="",
    metadata=None,
):
    user = request.user if getattr(request.user, "is_authenticated", False) else None
    event_metadata = request_metadata(request)
    if metadata:
        event_metadata.update(metadata)
    return InteractionEvent.objects.create(
        user=user,
        event_type=event_type,
        module=module,
        submodule=submodule,
        dashboard=dashboard,
        report=report,
        target_url=target_url or request.path,
        request_metadata=event_metadata,
    )
