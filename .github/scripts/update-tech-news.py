#!/usr/bin/env python3
"""GitHub Actions entrypoint — delegates to scripts/run_ingest.py."""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
subprocess.run([sys.executable, str(ROOT / "scripts" / "run_ingest.py")], check=True)
