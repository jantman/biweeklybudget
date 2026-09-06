# GitHub Actions Workflows

## 🧪 `run-tox-suite.yml`

**Triggers:** every PR; pushes to `master`; `workflow_dispatch`
**Purpose:** the tox suite (unit, acceptance, docs, migrations, docker) against a MariaDB
service container.

## 📦 `release.yml`

Build and publish. See the file.

## 🤖 `claude-pr-review.yml` and `claude-mention.yml`

These two look redundant and are not. **Do not delete one as a duplicate of the other.**

| | `claude-pr-review.yml` | `claude-mention.yml` |
|---|---|---|
| **Triggers** | `pull_request` | `issue_comment`, `issues`, `pull_request_review*` + `@claude` |
| **Asked for?** | No — reviews every PR unprompted | Yes — only when you write `@claude` |
| **Action mode** | agent (a `prompt` is supplied) | tag (no `prompt`) |
| **`contents:`** | `read` | `write` — it can push fixes |
| **`actions: read`** | yes — to read CI on the reviewed commit | yes — to read CI when asked |

The modes are why they cannot be one job. Supplying a `prompt` puts the action in agent mode
for *every* event it sees, so a single job with both triggers would answer `@claude` comments
in agent mode: no PR context, no tracking comment, and nothing posted back. They could share
one file as two guarded jobs; they are kept apart so each file's permissions and tools say
what they mean.

The 👀 reaction on an `@claude` comment comes from the Claude GitHub App acknowledging the
mention. It is **not** evidence that anything ran — the work happens in `claude-mention.yml`,
and if that workflow is missing or not yet on `master`, the eyes are all you ever get.

### This repo is public and has forks

Both workflows are guarded accordingly, and the guards are load-bearing:

- **`claude-pr-review.yml`** skips PRs from forks
  (`github.event.pull_request.head.repo.full_name == github.repository`). A fork's
  `pull_request` run gets no repository secrets, so `CLAUDE_CODE_OAUTH_TOKEN` would be
  empty and every such run would fail — and it would also hand `Bash` to an agent working
  in a stranger's checked-out tree. Fork PRs get reviewed by hand, or by pushing the branch
  to this repo.
- **`claude-mention.yml`** only fires for `OWNER`/`MEMBER`/`COLLABORATOR` authors. Without
  that, anyone on the internet could type `@claude` in an issue and get a `contents: write`
  agent run billed to the maintainer's account.

Do not switch the review workflow to `pull_request_target` to "fix" fork PRs — that runs
with secrets against untrusted code.

### Allowed tools

`--allowedTools` **adds to** the action's base tools (file operations, comment management,
read-only git) — it does not replace them. Each list is therefore only the delta, and
anything missing from it is a *silent* denial, not an error.

Two entries are load-bearing for this repo in particular:

- **`Skill`, in both files.** `/code-review:code-review` is itself a skill, so the review
  job denies its own review without it and improvises the plugin's steps by hand — which is
  how a run goes green having posted nothing. In `claude-mention.yml` it is needed for the
  15 committed skills under `.claude/skills/` (`speckit-*`), which are the documented
  feature workflow here and are present in the CI checkout; without it,
  `@claude run /speckit-tasks` is a no-op.
- **`mcp__github_ci__*`, in both files.** This is the point of
  `additional_permissions: actions: read` — it lets Claude read an actual
  `run-tox-suite.yml` failure rather than guess at a red X. That suite is long and
  DB-backed, so the difference is large. In `claude-pr-review.yml` it means the reviewer
  can see whether the suite passed on the commit it is reviewing; the `prompt` scopes that
  deliberately, so a test the diff broke is a finding but flakes and pre-existing failures
  are not, and a red suite never causes the review to be skipped.

The review job deliberately has no `Edit`/`Write`: it reads and comments. It also cannot run
this project's tests — `tox`/`pytest` need a MariaDB service container the job does not
have — so it reviews by reading, and `run-tox-suite.yml` remains what actually runs the
suite.

**Artifacts:** both upload `claude-<workflow>-logs-*`, containing `execution-output.json`
(the action's own transcript) and `sessions/` (the raw Claude Code session JSONL). The action
otherwise discards these with the runner, and the job log alone shows only `init` and
`result`. Reach for these first when a run is green but posted nothing. Note this repo is
public, so these artifacts and the `show_full_output` job logs are world-readable — they
carry full tool output, so don't put anything into CI you wouldn't publish.

**Re-review on new commits:** the upstream `/code-review` plugin stops without posting if
Claude has already commented on the PR, which would make every push after the first review a
silent no-op. `claude-pr-review.yml` overrides that in its `prompt` and scopes re-reviews to
the commits since Claude's last comment.

### Setup

Both need a `CLAUDE_CODE_OAUTH_TOKEN` repository secret and the Claude GitHub App installed
on the repo:

```bash
claude            # then: /install-github-app
```

Without the secret the action fails immediately on every PR.
