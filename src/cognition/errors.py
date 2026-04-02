"""Cognition error classes for the Simulatte cognitive loop."""


class PerceiveError(Exception):
    """Raised when perceive() fails after retry."""
    ...


class ReflectError(Exception):
    """Raised when reflect() fails after retry or when observations are insufficient."""
    ...


class DecideError(Exception):
    """Raised when decide() fails after retry."""
    ...
