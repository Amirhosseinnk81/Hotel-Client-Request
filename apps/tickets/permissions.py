# IsOperator now lives in apps.core.permissions (the single, shared
# source of truth for role-based permissions across the project).
# Re-exported here so existing imports (`from .permissions import
# IsOperator`) keep working without touching every call site.
from apps.core.permissions import IsOperator

__all__ = ["IsOperator"]
