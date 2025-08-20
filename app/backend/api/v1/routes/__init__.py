"""
API Routes for TradePulse.AI Professional Backend
ONLY ESSENTIAL ROUTES - NO COMPLEX DEPENDENCIES
"""

# ONLY import essential routes for professional backend
from . import health
from . import signals
from . import admin_runtime
from . import auth
from . import portfolio

__all__ = ["health", "signals", "admin_runtime", "auth", "portfolio"]
