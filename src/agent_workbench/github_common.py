from __future__ import annotations

import json
import subprocess
from pathlib import Path
from typing import Any


def run_command(args: list[str], *, check: bool = True) -> subprocess.CompletedProcess[str]:
    result = subprocess.run(args, capture_output=True, text=True)
    if check and result.returncode != 0:
        command = " ".join(args)
        details = result.stderr.strip() or result.stdout.strip() or "No command output."
        raise RuntimeError(f"Command failed ({result.returncode}): {command}\n{details}")
    return result


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
