"""Tests for IV DB stats script CI output."""

import subprocess
import sys
from pathlib import Path


def test_env_format_stdout_is_only_key_value_lines():
    """GitHub Actions parses stdout; log lines must not appear there."""
    root = Path(__file__).resolve().parent.parent
    script = root / "scripts" / "iv_db_stats.py"
    result = subprocess.run(
        [sys.executable, str(script), "--format", "env"],
        cwd=root,
        capture_output=True,
        text=True,
        check=False,
    )
    assert result.returncode == 0
    lines = [line for line in result.stdout.splitlines() if line.strip()]
    assert lines
    assert all("=" in line and line.split("=", 1)[0].startswith("IV_") for line in lines)
    assert "INFO" not in result.stdout
