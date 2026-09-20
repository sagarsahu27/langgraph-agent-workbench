# API returns 500 when invoice due date is omitted

## Summary

Creating an invoice without a `due_date` returns HTTP 500 instead of a validation error.

## Steps to reproduce

1. Start the sample billing API.
2. Submit `POST /api/invoices` with a customer ID and line items but no `due_date`.
3. Observe the response and service logs.

## Expected behavior

The API should return HTTP 400 with a validation message such as `due_date is required`.

## Actual behavior

The API returns HTTP 500 and the logs show a null dereference while calculating payment terms.

## Failure log

Use `scenarios/logs/invoice-null-due-date.log`.

## Agent command

```powershell
agent-workbench run-both --project . --issue-file .\scenarios\issues\invoice-null-due-date.md --log-file .\scenarios\logs\invoice-null-due-date.log
```

