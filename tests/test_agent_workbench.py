from pathlib import Path
from types import SimpleNamespace

import pytest

from agent_workbench.main import (
    build_diagnostic_fix_graph,
    build_triage_graph,
    create_project_snapshot,
    get_llm,
    read_issue,
    should_include,
)


class FakeChatModel:
    def __init__(self) -> None:
        self.prompts: list[str] = []

    def invoke(self, messages):
        self.prompts.append(messages[-1][1])
        if "Return concise Markdown" in messages[-1][1]:
            return SimpleNamespace(content="triage response")
        if "Identify the most likely root cause" in messages[-1][1]:
            return SimpleNamespace(content="diagnosis response")
        return SimpleNamespace(content="fix plan response")


def test_triage_graph_returns_triage_response():
    result = build_triage_graph(FakeChatModel()).invoke({"issue_text": "API returns 500"})

    assert result["triage"] == "triage response"
    assert result["final"] == "triage response"


def test_diagnostic_fix_graph_uses_project_snapshot(tmp_path: Path):
    (tmp_path / "pyproject.toml").write_text("[project]\nname='demo'\n", encoding="utf-8")
    src = tmp_path / "src"
    src.mkdir()
    (src / "app.py").write_text("def handler():\n    return 500\n", encoding="utf-8")

    result = build_diagnostic_fix_graph(FakeChatModel()).invoke(
        {"issue_text": "handler returns 500", "project_path": str(tmp_path)}
    )

    assert "pyproject.toml" in result["project_snapshot"]
    assert result["diagnosis"] == "diagnosis response"
    assert result["fix_plan"] == "fix plan response"
    assert "## Diagnosis" in result["final"]


def test_snapshot_skips_common_dependency_dirs(tmp_path: Path):
    (tmp_path / "README.md").write_text("# Demo\n", encoding="utf-8")
    node_modules = tmp_path / "node_modules"
    node_modules.mkdir()
    (node_modules / "ignored.js").write_text("ignored", encoding="utf-8")

    snapshot = create_project_snapshot(tmp_path)

    assert "README.md" in snapshot
    assert "node_modules" not in snapshot


def test_read_issue_appends_failure_logs(tmp_path: Path):
    issue_file = tmp_path / "issue.md"
    issue_file.write_text("API returns 500", encoding="utf-8")
    log_file = tmp_path / "failure.log"
    log_file.write_text("ValueError: due_date is required", encoding="utf-8")

    issue_text = read_issue(
        SimpleNamespace(issue=None, issue_file=str(issue_file), log_file=str(log_file))
    )

    assert "API returns 500" in issue_text
    assert "Failure logs:" in issue_text
    assert "ValueError: due_date is required" in issue_text


def test_should_include_supports_text_and_common_build_files(tmp_path: Path):
    dockerfile = tmp_path / "Dockerfile"
    dockerfile.write_text("FROM python:3.12\n", encoding="utf-8")
    image = tmp_path / "logo.png"
    image.write_bytes(b"not text")

    assert should_include(dockerfile, tmp_path)
    assert not should_include(image, tmp_path)


def test_get_llm_rejects_unknown_provider():
    with pytest.raises(ValueError, match="Unsupported provider"):
        get_llm("unknown-provider")
