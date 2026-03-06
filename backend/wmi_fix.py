"""Pytest plugin: fix Python 3.14 WMI deadlock on Windows.

platform._wmi_query() hangs indefinitely on some Windows machines with
Python 3.14. celery/utils/term.py calls platform.system() at import time
during Django app population, deadlocking the test runner.

Fix: inject a cached uname result so platform.system() never calls WMI.
Loaded via pytest.ini: addopts = -p wmi_fix
"""
import os
import platform
import sys

if sys.platform == "win32":
    _cache = platform.uname_result(
        "Windows",
        os.environ.get("COMPUTERNAME", ""),
        "",
        "",
        os.environ.get("PROCESSOR_ARCHITECTURE", ""),
    )
    _cache.__dict__["processor"] = os.environ.get("PROCESSOR_IDENTIFIER", "")
    platform._uname_cache = _cache
