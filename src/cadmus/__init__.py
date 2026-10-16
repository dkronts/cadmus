"""Cadmus — Greek grammar and syntax checker for local LLM output."""

__version__ = "0.0.8"

from .checker import CadmusChecker, Violation

__all__ = ["CadmusChecker", "Violation", "__version__"]
