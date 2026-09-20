from __future__ import annotations

import json
import subprocess
from pathlib import Path
from typing import Any


def run_command(args: list[str], *, check: bool = True) -> subprocess.CompletedProcess[str]:
    return subprocess.run(args, check=check, capture_output=True, text=True)


def run_gh_json(args: list[str]) -> Any:
    result = run_command(["gh", *args])
    if not result.stdout.strip():
        return None
    return json.loads(result.stdout)


def run_gh_text(args: list[str]) -> str:
    return run_command(["gh", *args]).stdout


def write_text_file(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")

