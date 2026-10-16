"""Cadmus — Greek grammar and syntax checker for local LLM output."""

__version__ = "0.0.13"

from .checker import CadmusChecker, Violation

__all__ = ["CadmusChecker", "Violation", "__version__"]
