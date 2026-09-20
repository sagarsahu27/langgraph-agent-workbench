from __future__ import annotations

import argparse
import os
import re
from pathlib import Path
from typing import Any

from agent_workbench.github_common import run_command, run_gh_json, write_text_file
from agent_workbench.main import build_diagnostic_fix_graph, build_triage_graph, get_llm


def build_issue_context(issue: dict[str, Any]) -> str:
    labels = ", ".join(label["name"] for label in issue.get("labels", [])) or "none"
    return f"""GitHub issue #{issue["number"]}: {issue["title"]}

URL: {issue["html_url"]}
Labels: {labels}

Body:
{issue.get("body") or "(no body provided)"}
"""


def build_issue_report(issue: dict[str, Any], triage: str, diagnosis: str, fix_plan: str) -> str:
    return f"""# Agent fix plan for issue #{issue["number"]}

Issue: [{issue["title"]}]({issue["html_url"]})

## Triage

{triage}

## Diagnosis

{diagnosis}

## Proposed fix plan

{fix_plan}

## Next steps

Review this plan before converting it into code changes. The workflow creates a draft PR intentionally so maintainers can decide whether the suggested approach is safe.
"""


def slugify(value: str, max_length: int = 48) -> str:
    slug = re.sub(r"[^a-z0-9]+", "-", value.lower()).strip("-")
    return (slug or "issue")[:max_length].strip("-")


def get_issue(repo: str, issue_number: int) -> dict[str, Any]:
    return run_gh_json(["api", f"repos/{repo}/issues/{issue_number}"])


def create_fix_plan_pr(repo: str, issue: dict[str, Any], report_path: Path) -> str:
    branch = f"agent/issue-{issue['number']}-{slugify(issue['title'])}"
    run_command(["git", "checkout", "-B", branch])
    run_command(["git", "add", str(report_path)])

    diff = run_command(["git", "diff", "--cached", "--quiet"], check=False)
    if diff.returncode == 0:
        existing = run_command(
            ["gh", "pr", "view", branch, "--repo", repo, "--json", "url", "--jq", ".url"],
            check=False,
        )
        return existing.stdout.strip() or "No changes to publish."

    run_command(
        [
            "git",
            "commit",
            "-m",
            f"Add agent fix plan for issue #{issue['number']}",
        ]
    )
    run_command(["git", "push", "--force-with-lease", "origin", branch])

    existing = run_command(
        ["gh", "pr", "view", branch, "--repo", repo, "--json", "url", "--jq", ".url"],
        check=False,
    )
    if existing.returncode == 0 and existing.stdout.strip():
        return existing.stdout.strip()

    body = f"""Automated draft PR with an agent-generated analysis and fix plan for #{issue["number"]}.

This PR is intentionally a draft and contains a reviewable plan, not an automatically applied code patch.
"""
    created = run_command(
        [
            "gh",
            "pr",
            "create",
            "--repo",
            repo,
            "--draft",
            "--base",
            "main",
            "--head",
            branch,
            "--title",
            f"Agent fix plan for #{issue['number']}: {issue['title']}",
            "--body",
            body,
        ]
    )
    return created.stdout.strip()


def run_issue_agent(
    repo: str,
    issue_number: int,
    provider: str | None,
    model: str | None,
    project: str,
    output_dir: Path,
    create_pr: bool,
) -> str:
    issue = get_issue(repo, issue_number)
    if "pull_request" in issue:
        return "Skipped: issue event points to a pull request."

    issue_context = build_issue_context(issue)
    llm = get_llm(provider, model)
    triage_result = build_triage_graph(llm).invoke({"issue_text": issue_context})
    enriched_issue = f"{issue_context}\n\nTriage:\n{triage_result['triage']}"
    fix_result = build_diagnostic_fix_graph(llm).invoke(
        {"issue_text": enriched_issue, "project_path": project}
    )

    report = build_issue_report(
        issue,
        triage_result["triage"],
        fix_result["diagnosis"],
        fix_result["fix_plan"],
    )
    report_path = output_dir / f"issue-{issue_number}-fix-plan.md"
    write_text_file(report_path, report)

    if create_pr:
        pr_url = create_fix_plan_pr(repo, issue, report_path)
        return f"Created draft PR: {pr_url}"

    return f"Wrote report: {report_path}"


def main() -> None:
    parser = argparse.ArgumentParser(description="Analyze a GitHub issue and optionally open a draft fix-plan PR.")
    parser.add_argument("--repo", required=True, help="Repository in owner/name format.")
    parser.add_argument("--issue-number", required=True, type=int)
    parser.add_argument("--provider", default=os.getenv("MODEL_PROVIDER", "openai"))
    parser.add_argument("--model", default=os.getenv("MODEL_NAME"))
    parser.add_argument("--project", default=".")
    parser.add_argument("--output-dir", default="agent-output/issues")
    parser.add_argument("--create-pr", action="store_true")
    args = parser.parse_args()

    result = run_issue_agent(
        args.repo,
        args.issue_number,
        args.provider,
        args.model,
        args.project,
        Path(args.output_dir),
        args.create_pr,
    )
    print(result)


if __name__ == "__main__":
    main()

