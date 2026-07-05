"""Pytest configuration for the OKF tooling test suite.

Adds the OKF scripts directory (the parent of this tests/ package) to
``sys.path`` so the tests can ``import validate, okf_common, visualize``
directly, exactly as the scripts import each other at runtime.
"""
import sys
from pathlib import Path

SCRIPTS_DIR = Path(__file__).resolve().parent.parent
if str(SCRIPTS_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPTS_DIR))
