# LangGraph agent workbench

This sample defines two LangGraph agents that can run on multiple model runtimes:

1. **Issue triage agent** - classifies an issue, estimates severity and priority, suggests labels, identifies likely owner/component, and asks for missing reproduction details.
2. **Diagnostic and fix agent** - inspects a target project, summarizes likely root causes, recommends focused checks, and drafts a safe fix plan or patch guidance.

Supported runtimes:

- **Ollama** for local models such as Qwen
- **OpenAI API**
- **Azure OpenAI**

## Prerequisites

Install Python 3.10 or newer.

For local Qwen, install and start Ollama, then pull a model:

```powershell
ollama pull qwen2.5-coder:7b
ollama serve
```

## Setup

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -e ".[dev]"
```

## Configure a runtime

Ollama with local Qwen:

```powershell
$env:MODEL_PROVIDER = "ollama"
$env:MODEL_NAME = "qwen2.5-coder:7b"
```

OpenAI:

```powershell
$env:MODEL_PROVIDER = "openai"
$env:MODEL_NAME = "gpt-4o-mini"
$env:OPENAI_API_KEY = "..."
```

Azure OpenAI:

```powershell
$env:MODEL_PROVIDER = "azure-openai"
$env:MODEL_NAME = "your-azure-openai-deployment"
$env:AZURE_OPENAI_ENDPOINT = "https://your-resource.openai.azure.com/"
$env:AZURE_OPENAI_API_KEY = "..."
```

## Run the agents

Triage an issue:

```powershell
agent-workbench triage --issue "The API returns 500 when creating an invoice without a due date."
```

Diagnose a project and produce a fix plan:

```powershell
agent-workbench diagnose-fix --project C:\path\to\project --issue "The API returns 500 when creating an invoice without a due date."
```

Run both agents in sequence:

```powershell
agent-workbench run-both --project C:\path\to\project --issue-file .\issue.txt
```

Include failure logs in the issue context:

```powershell
agent-workbench run-both --project . --issue-file .\scenarios\issues\invoice-null-due-date.md --log-file .\scenarios\logs\invoice-null-due-date.log
```

You can also pass runtime settings directly:

```powershell
agent-workbench triage --provider openai --model gpt-4o-mini --issue "Login fails after password reset."
```

## Test

```powershell
pytest
```

## GitHub Actions automation

This repo includes two optional workflows:

- **Agent issue analysis** runs when an issue is opened, edited, reopened, or labeled. It triages the issue, diagnoses the repository, writes an agent fix plan under `agent-output/issues/`, and opens a draft PR for maintainer review.
- **Agent PR review** runs when a pull request is opened or updated. It reviews the diff and posts or updates a PR comment.

Configure repository secrets/variables before enabling the workflows:

```text
OPENAI_API_KEY              # required when MODEL_PROVIDER=openai
AZURE_OPENAI_API_KEY        # required when MODEL_PROVIDER=azure-openai
AZURE_OPENAI_ENDPOINT       # required when MODEL_PROVIDER=azure-openai
MODEL_PROVIDER              # repository variable: openai or azure-openai
MODEL_NAME                  # repository variable: model name or Azure deployment
AZURE_OPENAI_API_VERSION    # optional repository variable
```

The issue workflow intentionally creates a **draft PR with a fix plan**, not an unreviewed code patch. Convert the plan into code after review.

The diagnostic agent is intentionally conservative: it reads project files and produces a plan, but it does not mutate the target project. Use its output as a reviewable patch plan before making changes.
