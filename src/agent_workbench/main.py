from __future__ import annotations

import argparse
import json
import os
from pathlib import Path
from typing import Any, Literal, Protocol, TypedDict

from langgraph.graph import END, StateGraph


DEFAULT_PROVIDER = "ollama"
DEFAULT_OLLAMA_MODEL = "qwen3:4b"
DEFAULT_OPENAI_MODEL = "gpt-4o-mini"
DEFAULT_AZURE_OPENAI_API_VERSION = "2024-08-01-preview"

TEXT_EXTENSIONS = {
    ".cs",
    ".go",
    ".java",
    ".js",
    ".json",
    ".jsx",
    ".log",
    ".md",
    ".php",
    ".py",
    ".rb",
    ".rs",
    ".toml",
    ".ts",
    ".tsx",
    ".txt",
    ".yaml",
    ".yml",
}
SKIP_DIRS = {
    ".git",
    ".hg",
    ".mypy_cache",
    ".pytest_cache",
    ".ruff_cache",
    ".venv",
    "bin",
    "build",
    "dist",
    "node_modules",
    "obj",
    "target",
    "venv",
    "__pycache__",
}

Provider = Literal["ollama", "openai", "azure-openai"]


class ChatModel(Protocol):
    def invoke(self, messages: list[tuple[str, str]]) -> Any:
        ...


class AgentState(TypedDict, total=False):
    issue_text: str
    project_path: str
    project_snapshot: str
    triage: str
    diagnosis: str
    fix_plan: str
    final: str


def get_llm(
    provider: str | None = None,
    model: str | None = None,
    temperature: float = 0.1,
) -> ChatModel:
    selected_provider = (provider or os.getenv("MODEL_PROVIDER") or DEFAULT_PROVIDER).lower()

    if selected_provider == "ollama":
        from langchain_ollama import ChatOllama

        selected_model = model or os.getenv("MODEL_NAME") or os.getenv("QWEN_MODEL") or DEFAULT_OLLAMA_MODEL
        reasoning_setting = os.getenv("OLLAMA_REASONING")
        reasoning = (
            reasoning_setting.lower() in {"1", "true", "yes", "on"}
            if reasoning_setting is not None
            else False if selected_model.startswith("qwen3") else None
        )
        return ChatOllama(
            model=selected_model,
            base_url=os.getenv("OLLAMA_BASE_URL", "http://localhost:11434"),
            reasoning=reasoning,
            temperature=temperature,
        )

    if selected_provider == "openai":
        from langchain_openai import ChatOpenAI

        return ChatOpenAI(
            model=model or os.getenv("MODEL_NAME") or DEFAULT_OPENAI_MODEL,
            temperature=temperature,
        )

    if selected_provider == "azure-openai":
        from langchain_openai import AzureChatOpenAI

        deployment = model or os.getenv("AZURE_OPENAI_DEPLOYMENT") or os.getenv("MODEL_NAME")
        if not deployment:
            raise ValueError("Set --model, MODEL_NAME, or AZURE_OPENAI_DEPLOYMENT for Azure OpenAI.")
        return AzureChatOpenAI(
            azure_deployment=deployment,
            api_version=os.getenv("AZURE_OPENAI_API_VERSION", DEFAULT_AZURE_OPENAI_API_VERSION),
            temperature=temperature,
        )

    supported = ", ".join(["ollama", "openai", "azure-openai"])
    raise ValueError(f"Unsupported provider '{selected_provider}'. Supported providers: {supported}.")


def invoke_text(llm: ChatModel, system_prompt: str, user_prompt: str) -> str:
    response = llm.invoke(
        [
            ("system", system_prompt),
            ("human", user_prompt),
        ]
    )
    return str(response.content).strip()


def build_triage_graph(llm: ChatModel):
    graph = StateGraph(AgentState)

    def triage_issue(state: AgentState) -> AgentState:
        prompt = f"""
Issue:
{state["issue_text"]}

Return concise Markdown with these fields:
- Summary
- Category
- Severity
- Priority
- Suggested labels
- Likely component or owner
- Missing information
- Recommended next action
"""
        triage = invoke_text(
            llm,
            "You are an issue triage agent. Be decisive, concise, and practical.",
            prompt.strip(),
        )
        return {"triage": triage, "final": triage}

    graph.add_node("triage_issue", triage_issue)
    graph.set_entry_point("triage_issue")
    graph.add_edge("triage_issue", END)
    return graph.compile()


def build_diagnostic_fix_graph(llm: ChatModel):
    graph = StateGraph(AgentState)

    def inspect_project(state: AgentState) -> AgentState:
        project_path = Path(state["project_path"]).resolve()
        snapshot = create_project_snapshot(project_path)
        return {"project_snapshot": snapshot}

    def diagnose_issue(state: AgentState) -> AgentState:
        prompt = f"""
Issue:
{state["issue_text"]}

Project snapshot:
{state["project_snapshot"]}

Identify the most likely root cause areas. Include:
- Relevant files or modules to inspect first
- Suspected failure path
- Commands or checks to reproduce
- Risks and assumptions
"""
        diagnosis = invoke_text(
            llm,
            "You are a senior diagnostic agent for software projects. Ground conclusions in the project snapshot.",
            prompt.strip(),
        )
        return {"diagnosis": diagnosis}

    def plan_fix(state: AgentState) -> AgentState:
        prompt = f"""
Issue:
{state["issue_text"]}

Diagnosis:
{state["diagnosis"]}

Project snapshot:
{state["project_snapshot"]}

Create a minimal, reviewable fix plan. If code changes are clear, include patch-style guidance,
but do not invent files or APIs that are not supported by the snapshot.
"""
        fix_plan = invoke_text(
            llm,
            "You are a fix agent. Prefer surgical changes, tests, and safe rollback guidance.",
            prompt.strip(),
        )
        final = f"## Diagnosis\n\n{state['diagnosis']}\n\n## Fix plan\n\n{fix_plan}"
        return {"fix_plan": fix_plan, "final": final}

    graph.add_node("inspect_project", inspect_project)
    graph.add_node("diagnose_issue", diagnose_issue)
    graph.add_node("plan_fix", plan_fix)
    graph.set_entry_point("inspect_project")
    graph.add_edge("inspect_project", "diagnose_issue")
    graph.add_edge("diagnose_issue", "plan_fix")
    graph.add_edge("plan_fix", END)
    return graph.compile()


def create_project_snapshot(project_path: Path, max_files: int = 80, max_chars: int = 24_000) -> str:
    if not project_path.exists():
        raise FileNotFoundError(f"Project path does not exist: {project_path}")
    if not project_path.is_dir():
        raise NotADirectoryError(f"Project path is not a directory: {project_path}")

    files: list[Path] = []
    for path in project_path.rglob("*"):
        if should_include(path, project_path):
            files.append(path)

    manifest_names = {
        "package.json",
        "pyproject.toml",
        "requirements.txt",
        "go.mod",
        "Cargo.toml",
        "pom.xml",
        "build.gradle",
        "README.md",
    }
    files.sort(key=lambda p: (p.name not in manifest_names, len(p.parts), str(p).lower()))
    selected_files = files[:max_files]

    parts = [f"Project: {project_path}", "Files:"]
    parts.extend(f"- {file.relative_to(project_path)}" for file in selected_files)
    parts.append("\nSelected file excerpts:")

    char_count = sum(len(part) for part in parts)
    for file in selected_files:
        if char_count >= max_chars:
            break
        try:
            content = file.read_text(encoding="utf-8", errors="replace")
        except OSError:
            continue
        excerpt = content[:2_000]
        block = f"\n--- {file.relative_to(project_path)} ---\n{excerpt}"
        parts.append(block)
        char_count += len(block)

    return "\n".join(parts)


def should_include(path: Path, root: Path) -> bool:
    if not path.is_file():
        return False
    relative_parts = path.relative_to(root).parts
    if any(part in SKIP_DIRS for part in relative_parts):
        return False
    if path.suffix.lower() in TEXT_EXTENSIONS:
        return True
    return path.name in {"Dockerfile", "Makefile"}


def read_issue(args: argparse.Namespace) -> str:
    if args.issue_file:
        issue_text = Path(args.issue_file).read_text(encoding="utf-8").strip()
    elif args.issue:
        issue_text = args.issue.strip()
    else:
        raise ValueError("Provide --issue or --issue-file.")

    if args.log_file:
        log_text = Path(args.log_file).read_text(encoding="utf-8", errors="replace").strip()
        return f"{issue_text}\n\nFailure logs:\n```text\n{log_text}\n```"

    return issue_text


def print_result(result: dict[str, Any], as_json: bool) -> None:
    if as_json:
        print(json.dumps(result, indent=2))
        return
    print(result.get("final") or result)


def add_common_model_args(parser: argparse.ArgumentParser) -> None:
    parser.add_argument(
        "--provider",
        choices=["ollama", "openai", "azure-openai"],
        default=os.getenv("MODEL_PROVIDER", DEFAULT_PROVIDER),
        help="Model runtime provider.",
    )
    parser.add_argument("--model", default=os.getenv("MODEL_NAME"), help="Model name or Azure deployment.")
    parser.add_argument("--temperature", type=float, default=0.1, help="Model temperature.")
    parser.add_argument("--json", action="store_true", help="Print raw graph output as JSON.")


def main() -> None:
    parser = argparse.ArgumentParser(description="Run LangGraph issue triage and diagnostic agents.")
    add_common_model_args(parser)

    subparsers = parser.add_subparsers(dest="command", required=True)

    triage = subparsers.add_parser("triage", help="Triage an issue.")
    triage.add_argument("--issue")
    triage.add_argument("--issue-file")
    triage.add_argument("--log-file", help="Optional failure log file to include in the issue context.")

    diagnose = subparsers.add_parser("diagnose-fix", help="Diagnose a project and propose a fix.")
    diagnose.add_argument("--project", default=".")
    diagnose.add_argument("--issue")
    diagnose.add_argument("--issue-file")
    diagnose.add_argument("--log-file", help="Optional failure log file to include in the issue context.")

    both = subparsers.add_parser("run-both", help="Run issue triage, then diagnose and propose a fix.")
    both.add_argument("--project", default=".")
    both.add_argument("--issue")
    both.add_argument("--issue-file")
    both.add_argument("--log-file", help="Optional failure log file to include in the issue context.")

    args = parser.parse_args()
    llm = get_llm(args.provider, args.model, args.temperature)
    issue_text = read_issue(args)

    if args.command == "triage":
        result = build_triage_graph(llm).invoke({"issue_text": issue_text})
        print_result(result, args.json)
        return

    if args.command == "diagnose-fix":
        result = build_diagnostic_fix_graph(llm).invoke(
            {"issue_text": issue_text, "project_path": args.project}
        )
        print_result(result, args.json)
        return

    triage_result = build_triage_graph(llm).invoke({"issue_text": issue_text})
    enriched_issue = f"{issue_text}\n\nTriage:\n{triage_result['triage']}"
    fix_result = build_diagnostic_fix_graph(llm).invoke(
        {"issue_text": enriched_issue, "project_path": args.project}
    )
    combined = {
        "issue_text": issue_text,
        "triage": triage_result["triage"],
        "diagnosis": fix_result["diagnosis"],
        "fix_plan": fix_result["fix_plan"],
        "final": f"## Triage\n\n{triage_result['triage']}\n\n{fix_result['final']}",
    }
    print_result(combined, args.json)


if __name__ == "__main__":
    main()
