"""Shared FastAPI dependencies."""

from src.api.auth import get_current_user, require_admin  # re-export
from src.db.pool import get_pool

__all__ = ["get_current_user", "require_admin", "get_pool"]
