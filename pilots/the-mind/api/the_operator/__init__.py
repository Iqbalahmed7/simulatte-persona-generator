"""the_operator — Prospect Twin module for the Persona Generator platform.

Activated by OPERATOR_ENABLED=true env var. When disabled, routes return 404.
Do not import this package unless OPERATOR_ENABLED=true.
"""
from the_operator.router import operator_router  # noqa: F401
