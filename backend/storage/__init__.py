"""
Storage Package

Provides abstract storage interface and implementations for backend components.
"""

from .base import Storage
from .memory import MemoryStorage

__all__ = ["Storage", "MemoryStorage"]
