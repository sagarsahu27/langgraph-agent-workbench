import sys

import pytest

from agent_workbench.github_common import run_command
from agent_workbench.github_issue_agent import build_issue_context, build_issue_report, slugify
from agent_workbench.github_pr_agent import COMMENT_MARKER, build_pr_review_prompt, format_review_comment


def test_issue_report_contains_triage_diagnosis_and_fix_plan():
    issue = {
        "number": 7,
        "title": "API returns 500",
        "html_url": "https://github.com/example/repo/issues/7",
        "body": "Failure body",
        "labels": [{"name": "bug"}],
    }

    context = build_issue_context(issue)
    report = build_issue_report(issue, "triage", "diagnosis", "fix")

    assert "Labels: bug" in context
    assert "issue #7" in report
    assert "triage" in report
    assert "diagnosis" in report
    assert "fix" in report


def test_slugify_is_branch_safe():
    assert slugify("API returns 500 when due_date is missing!") == "api-returns-500-when-due-date-is-missing"


def test_pr_review_prompt_and_comment_marker():
    pr = {
        "number": 3,
        "title": "Fix invoice validation",
        "html_url": "https://github.com/example/repo/pull/3",
        "body": "Adds validation.",
        "user": {"login": "octocat"},
    }
    files = [{"filename": "src/app.py", "additions": 10, "deletions": 2}]

    prompt = build_pr_review_prompt(pr, files, "diff --git a/src/app.py b/src/app.py")
    comment = format_review_comment("Looks good.")

    assert "Fix invoice validation" in prompt
    assert "src/app.py" in prompt
    assert COMMENT_MARKER in comment
    assert "Looks good." in comment


def test_run_command_includes_process_error_output():
    with pytest.raises(RuntimeError, match="expected failure"):
        run_command([sys.executable, "-c", "import sys; sys.stderr.write('expected failure'); sys.exit(2)"])
