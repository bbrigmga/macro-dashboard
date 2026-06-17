"""
NumPy API shims for dependencies that still expect removed members.

NumPy 2.4 removed ``np.in1d`` (use ``np.isin``). Older scipy releases import it
via lazy attribute lookup and fail with ``AttributeError`` on import.
"""

from __future__ import annotations

import numpy as np


def apply_numpy_compat() -> None:
    """Patch removed NumPy aliases expected by scipy and other libraries."""
    if not hasattr(np, "in1d"):
        np.in1d = np.isin  # type: ignore[attr-defined]


apply_numpy_compat()
