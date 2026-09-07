# Contract: the `addtrans` console script

New console entry point: `addtrans = biweeklybudget.addtrans:main`.

It creates a Transaction by calling `POST /forms/transaction` over HTTP. It does **not**
touch the database, does not import `biweeklybudget.db`, and does not require a settings
module — the whole point is to exercise the published API the way external tooling would.

## Usage

```text
usage: addtrans [-h] [-v] [-U URL] [-d DATE] -b BUDGET [-b BUDGET ...]
                [-n NOTES] [-t SALES_TAX] [-p CREDIT_PAYMENT_ACCT]
                [--no-budget-impact] [--dry-run]
                ACCOUNT AMOUNT DESCRIPTION
```

### Positional arguments

| Argument | Meaning |
|----------|---------|
| `ACCOUNT` | Account name or ID to book the transaction against. |
| `AMOUNT` | Transaction amount. Sent verbatim; the server accepts `123.45`, `$1,234.56`, `1,234.56`. |
| `DESCRIPTION` | Transaction description. |

### Options

| Option | Meaning |
|--------|---------|
| `-b`, `--budget BUDGET` | Repeatable, at least one required. Either `NAME` / `ID`, or `NAME=AMOUNT` / `ID=AMOUNT` to split. With exactly one `-b` and no `=AMOUNT`, the whole transaction amount is allocated to it. With more than one `-b`, every one must carry an `=AMOUNT`. |
| `-d`, `--date DATE` | `YYYY-MM-DD`. Defaults to today. |
| `-n`, `--notes NOTES` | Free-text notes. Defaults to the empty string, which the endpoint requires to be present. |
| `-t`, `--sales-tax AMOUNT` | Sales tax. Omitted from the payload when not given. |
| `-p`, `--credit-payment-acct ACCOUNT` | Name or ID of the credit account this transaction pays. |
| `--no-budget-impact` | Mark the transaction as not counting against its budget. |
| `-U`, `--url URL` | Base URL of the application. Default: `$BIWEEKLYBUDGET_URL`, else `http://127.0.0.1:8080`. |
| `--dry-run` | Print the JSON that would be posted, and exit 0 without posting. |
| `-v`, `--verbose` | Once for INFO, twice for DEBUG. Matches the project's other scripts. |
| `-h`, `--help` | Usage. |

### Budget-name caveat

Because `-b` splits on the first `=`, a Budget whose *name* contains `=` must be given by
ID. Documented, not worked around; no such name is plausible and inventing an escape
syntax for it would cost more than it saves.

## Behaviour

| Situation | stdout/stderr | Exit |
|-----------|---------------|------|
| Transaction created | `Created Transaction <id>` plus the server's success message | `0` |
| `--dry-run` | The JSON payload, pretty-printed | `0` |
| Server returned `success: false` with `errors` | One line per field per error, e.g. `budgets: Budget "Nope" is invalid.` | `1` |
| Server returned `success: false` with `error_message` | That message | `1` |
| More than one `-b` and any lacks `=AMOUNT` | Usage error from argparse | `2` |
| Connection refused, timeout, DNS failure | A one-line explanation naming the URL. No traceback. | `1` |
| Non-200 status, or a body that is not JSON | The status and a truncated body. No traceback. | `1` |

## Examples

```bash
# Simplest: whole amount to one budget, dated today
addtrans CHASE 123.45 'Groceries' -b Food

# Split across budgets, explicit date and notes
addtrans CHASE 123.45 'Grocery run' -d 2026-09-07 \
    -b Food=100.00 -b Household=23.45 -n 'weekly shop'

# A credit card payment, against a remote instance
addtrans -U http://budget.example.com:8080 \
    'BankOne Checking' 500.00 'CHASE payment' \
    -b 'Credit Card Payments' -p CHASE

# See what would be sent, without sending it
addtrans CHASE 10.00 'test' -b Food --dry-run
```
