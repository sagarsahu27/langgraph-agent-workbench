# Agent fix plan for issue #1

Issue: [API returns 500 when invoice due date is omitted](https://github.com/sagarsahu27/langgraph-agent-workbench/issues/1)

## Triage

```markdown
# Issue Triage Response

## Summary
API returns 500 when invoice due date is omitted

## Category
bug

## Severity
high

## Priority
critical

## Suggested labels
bug, test-scenario, agent-demo

## Likely component or owner
agent-demo (likely related to invoice processing logic)

## Missing information
- Detailed error logs for validation logic
- Expected behavior clarification
- Test scenario for validation error handling

## Recommended next action
Implement validation check for `due_date` in invoice creation, return HTTP 400 with appropriate error message, and ensure proper logging for validation failures.
```

## Diagnosis

# Root Cause Area Identification

## Relevant Files/Modules to Inspect First
- `src/agent_workbench/github_common.py` (contains common utilities for GitHub agents)
- `src/agent_workbench/github_issue_agent.py` (handles issue triage and reporting)
- `src/agent_workbench/github_pr_agent.py` (handles PR review and feedback)
- `src/agent_workbench/main.py` (main execution logic for agents)
- `src/agent_workbench/agent_workbench.egg-info/entry_points.txt` (contains agent entry points)

## Suspected Failure Path
The failure path is likely in the `run-both` command execution logic, specifically in the `agent_workbench` module. The core issue is that when an issue file is provided, the `run-both` command is not properly handling the validation logic for required fields, particularly the `due_date` field in invoice creation.

## Commands/Checks to Reproduce
To reproduce the issue, you can run the following command:
```powershell
agent-workbench run-both --project . --issue-file .\scenarios\issues\invoice-null-due-date.md --log-file .\scenarios\logs\invoice-null-due-date.log
```
This will execute the agent workflow, including the issue triage, diagnosis, and fix plan generation, and will generate the failure logs in the specified directory.

## Risks and Assumptions
- The issue is specific to the `run-both` command execution logic when an issue file is provided
- The failure is not caused by external factors (e.g., model runtime issues)
- The validation logic for `due_date` is correctly implemented in the agent code
- The failure logs contain sufficient information to identify the root cause

## Next Steps
1. Inspect the `run-both` command execution logic to identify where the `due_date` validation is being skipped
2. Check the failure logs for the exact point where the null dereference occurs
3. Implement the validation check for `due_date` in the `run-both` command execution logic
4. Ensure proper logging for validation failures to capture the exact error message and stack trace

## Proposed fix plan

# Fix Plan for API Error When Invoice Due Date is Omitted

## Summary
The API returns 500 when invoice due date is omitted instead of 400 validation error. Need to add validation check for `due_date` in invoice creation.

## Proposed Fix

### 1. Add Validation Check for `due_date`
Add a validation check in the `run-both` command execution logic to ensure `due_date` is not omitted.

### 2. Return HTTP 400 with Validation Error
Modify the logic to return HTTP 400 with a validation error message when `due_date` is missing.

### 3. Proper Logging
Ensure the validation failure is logged with the exact error message and stack trace.

## Patch Guidance

### 1. Add Validation Check in `run-both` Logic
Add the following code to the `run-both` command execution logic in `src/agent_workbench/main.py`:

```python
if not invoice.get('due_date'):
    raise ValueError("due_date is required")
```

### 2. Return HTTP 400 with Validation Error
Modify the logic to return HTTP 400 with a validation error message:

```python
if not invoice.get('due_date'):
    return HTTP_400, "due_date is required"
```

### 3. Ensure Proper Logging
Add logging for validation failures in `src/agent_workbench/main.py`:

```python
if not invoice.get('due_date'):
    logging.error("Validation failed: due_date is required")
    return HTTP_400, "due_date is required"
```

## Verification Steps

1. Run the `run-both` command with the issue file:
   ```powershell
   agent-workbench run-both --project . --issue-file .\scenarios\issues\invoice-null-due-date.md --log-file .\scenarios\logs\invoice-null-due-date.log
   ```

2. Verify the API returns HTTP 400 with the validation error message.

3. Check the logs for the validation failure message and stack trace.

## Notes
- This fix assumes the validation logic is correctly implemented in the agent code.
- The fix does not modify the actual API logic, only the `run-both` command execution logic.

## Next steps

Review this plan before converting it into code changes. The workflow creates a draft PR intentionally so maintainers can decide whether the suggested approach is safe.
