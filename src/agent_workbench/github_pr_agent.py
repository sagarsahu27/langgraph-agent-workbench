from __future__ import annotations

import argparse
import os
from typing import Any

from agent_workbench.github_common import run_command, run_gh_json
from agent_workbench.main import get_llm, invoke_text


COMMENT_MARKER = "<!-- agent-workbench-pr-review -->"
MAX_DIFF_CHARS = 24_000


def build_pr_review_prompt(pr: dict[str, Any], files: list[dict[str, Any]], diff: str) -> str:
    changed_files = "\n".join(
        f"- {file['filename']} (+{file.get('additions', 0)} -{file.get('deletions', 0)})"
        for file in files
    )
    return f"""Review this pull request for correctness, regressions, missing tests, and risky behavior.

PR #{pr["number"]}: {pr["title"]}
Author: {pr.get("user", {}).get("login", "unknown")}
URL: {pr["html_url"]}

Body:
{pr.get("body") or "(no body provided)"}

Changed files:
{changed_files or "(no file metadata available)"}

Diff:
```diff
{diff[:MAX_DIFF_CHARS]}
```

Return concise Markdown with:
- Summary
- High-confidence findings
- Test recommendations
- Merge readiness
"""


def format_review_comment(review: str) -> str:
    return f"""{COMMENT_MARKER}
## Agent workbench PR review

{review}
"""


def upsert_pr_comment(repo: str, pr_number: int, body: str) -> str:
    comments = run_gh_json(["api", f"repos/{repo}/issues/{pr_number}/comments", "--paginate"])
    for comment in comments or []:
        if COMMENT_MARKER in (comment.get("body") or ""):
            run_command(
                [
                    "gh",
                    "api",
                    "--method",
                    "PATCH",
                    f"repos/{repo}/issues/comments/{comment['id']}",
                    "-f",
                    f"body={body}",
                ]
            )
            return comment["html_url"]

    created = run_gh_json(
        [
            "api",
            "--method",
            "POST",
            f"repos/{repo}/issues/{pr_number}/comments",
            "-f",
            f"body={body}",
        ]
    )
    return created["html_url"]


def run_pr_review(repo: str, pr_number: int, provider: str | None, model: str | None) -> str:
    pr = run_gh_json(["api", f"repos/{repo}/pulls/{pr_number}"])
    files = run_gh_json(["api", f"repos/{repo}/pulls/{pr_number}/files", "--paginate"])
    diff = run_command(["gh", "pr", "diff", str(pr_number), "--repo", repo]).stdout

    llm = get_llm(provider, model)
    review = invoke_text(
        llm,
        "You are a careful code review agent. Report only actionable, high-confidence observations.",
        build_pr_review_prompt(pr, files or [], diff),
    )
    return upsert_pr_comment(repo, pr_number, format_review_comment(review))


def main() -> None:
    parser = argparse.ArgumentParser(description="Run agent review for a GitHub pull request.")
    parser.add_argument("--repo", required=True, help="Repository in owner/name format.")
    parser.add_argument("--pr-number", required=True, type=int)
    parser.add_argument("--provider", default=os.getenv("MODEL_PROVIDER", "openai"))
    parser.add_argument("--model", default=os.getenv("MODEL_NAME"))
    args = parser.parse_args()

    print(run_pr_review(args.repo, args.pr_number, args.provider, args.model))


if __name__ == "__main__":
    main()

