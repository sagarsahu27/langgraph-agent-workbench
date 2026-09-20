# Background diagnostic worker times out after retry storm

## Summary

The diagnostic worker repeatedly retries the same project scan after a transient dependency timeout, then eventually fails the job.

## Steps to reproduce

1. Queue a diagnostic scan for a project with at least 50 source files.
2. Simulate a transient timeout from the dependency metadata endpoint.
3. Let the worker process retries.

## Expected behavior

The worker should back off, preserve the original failure context, and complete or fail once with a clear diagnostic message.

## Actual behavior

The worker retries quickly, exhausts the retry budget, and emits duplicate error messages with conflicting job states.

## Failure log

Use `scenarios/logs/worker-timeout-after-retry.log`.

## Agent command

```powershell
agent-workbench run-both --project . --issue-file .\scenarios\issues\worker-timeout-after-retry.md --log-file .\scenarios\logs\worker-timeout-after-retry.log
```

