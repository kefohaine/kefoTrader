# Agent operating guide

Kept portable — generic rules that apply to any project using this template.
**Adapted for kefoTrader:** this repo has a **flat layout** (no `docs/` folder). Project-specific facts (setup, layout, usage, risk gates) live in `README.md` instead of `docs/GUIDE.md`. Rules that reference project-specific docs that don't exist here are noted in place.

When solutions compete, prefer: **secure › correct › reliable › reversible › simple › resource-efficient › maintainable**. Inspect before changing; never assume when you can look. Read it before making changes.

## Safety rules

These are non-negotiable. Follow them on every task. Project-specific facts (paths, recipe names) belong in `README.md`, never in these rules.

1. **Never delete or disable any critical service or file without explicit operator approval.** Critical files for this repo: `install.sh`, `README.md`, `config.yaml` (via installer only), `trading/*.py`, `cli/*.py`, `tests/*.py`, `paper.sh`, `live.sh`. Do not remove them without asking.
2. **Stay silent while doing tasks.** Do not narrate progress, do not print status updates, do not summarize what you just did. Run commands, edit files, and only emit text when you need a decision from the operator or are reporting a blocker. Output should be minimal — the work product speaks for itself.
3. **Push at milestones, before destructive ops, and when the prompt is done.** Before any hard-to-reverse operation (deleting files, force-recreating containers, `systemctl` changes, DB/schema changes, firewall edits), first commit and push. After reaching a milestone or completing the prompt, also commit and push. Don't wait for the operator to ask. If a push fails, fix it before proceeding. The canonical git commands for this repo: `git add .`, `git commit -m "<one-sentence>"`, `git push`. Raw `git` is used sparingly here — there are no `make` recipes or containers.
4. **Doc maintenance is first-class work, not a cleanup step.** Updating documentation is as important as working on the repo. Every system change, refactor, or operational decision MUST be followed by a doc audit — see the doc-audit workflow in "Before finishing a task" for the concrete procedure (walk every `.md`, diff against source, apply the three prongs). A push that leaves stale `.md` content is the same failure mode as a push that breaks the build.
5. **Minimize token usage.** Be extremely efficient: short, accurate, and understanding. No filler, no preamble, no restating the question, no recaps. Batch tool calls that can run in parallel. Read only the file regions you need. Prefer one precise edit over rewriting whole sections. Answer in as few words as the task allows.
6. **When an issue is explicitly intended by the operator or documented as a deliberate feature/design choice, document the rationale rather than treating it as a bug.** Example: auto-execute defaults to `false` (safe off). Record it so future agents don't "correct" it — e.g. in `README.md`.
7. **Minimize web searches.** Only fetch a URL when the answer is not already in the repo or your own knowledge. Prefer reading local files and reasoning.
8. **Never use user-facing data services for agent purposes.** Any service that hosts files or stores data for a user is user-only. Do not create records, upload files, write to databases, or store any data through these services for testing or debugging. Verify changes with read-only checks and roll back test artifacts immediately if created by mistake.
9. **Never read secrets, credentials, or sensitive user data.** `config.yaml` is the operator-only secret store; it is gitignored and must never leave this machine. Never reproduce a secret's *value* in a response, log, commit, or doc — refer to where it lives. If a task requires knowing a value from a secret file, ask the operator to provide it instead.
10. **Network-listener / route changes must end with a working state.** *N/A for this CLI-only repo — there is no container/host-port routing.* Skip this rule's smoke/reload steps; instead verify the affected launcher or MCP server runs to completion.
11. **After a debug hell, record the lesson** — a debug hell is anything that took multiple non-obvious hops to root-cause. This repo has no `docs/GUIDE.md`, so record the lesson as a short, grep-able `# GOTCHA` or `# FIXME` comment in the relevant file (with the symptom, root cause, and one-line takeaway) and notify the operator. Don't write a novel in commit messages — one sentence per change.
12. **Pause and reassess before irreversible or high-impact actions.** Deleting data; changing auth; exposing a service publicly; rewriting Git history; destroying infrastructure. These need explicit operator intent.
13. **Least privilege.** Use root only when the task needs it; never broaden permissions (sudoers, container capabilities, file modes, firewall) to work around a temporary problem.
14. **Dependencies.** Prefer something already present, or the official package/repo. Never pipe a remote script into a shell when a signed package exists. Know what a dependency is, where it comes from and what it changes before adding it.
15. **No fabrication.** Never report a change, test, or result you did not actually produce. If a test could not be run, say so and why.
16. **The `config.yaml` file is operator-only state, never agent-edited.** Agent changes are confined to tracked repo paths. Secrets must be written only through `./install.sh`, which prompts for them. Before committing: `git diff` must show no secrets and `config.yaml` must not be touched by the diff (the installer rewrites it).
17. **Stay global — derive from the live system, never hardcode instance specifics.** Everything that can change over time (API keys, base URLs, ports, paths) must be read from config or prompted, not written as fixed values. The installer (`install.sh`) already follows this: it prompts for every secret and writes `config.yaml` from those values. Future installers or scripts must do the same — prefer prompting with a sensible default over hardcoding.
18. **No runtime snapshots.** Don't write "currently running" or "healthy" — drifts the moment a service stops. Describe steady-state config, not transient state.
19. **No dead records, fallbacks, or "now removed" commentary.** Anything that isn't real anymore (a retired path, an old name, a superseded config) must be deleted from the repo, the host, and the docs. Never write "X worked Y way, now removed" — if X is gone, remove it and its references; git history keeps the record.
20. **Image files are opt-in, per task.** Never open, view, or inspect image files by default — they can carry personal data. Only read them with explicit, task-scoped operator authorization.
21. **No new listeners without an explicit operator request.** Don't bind to a new port, don't split listeners per-host, don't invent a new global block. The MCP stdio server (`cli/alpaca_mcp.py`) and launchers (`paper.sh`/`live.sh`) are the only entry points; add new ones only with approval.

## Boundaries between docs

This repo is flat: only `README.md` (project facts) and `AGENTS.md` (agent rules) exist. Don't blur them.

- **`README.md`** — the GitHub repo page and the project manual. What the project is, what it runs, how to deploy it, how to use it, the file layout, and risk-gate defaults. Short and factual: no verbose architecture prose. This is the **only** place project-specific facts live (in place of `docs/GUIDE.md`).
- **`AGENTS.md`** (this file) — agent-facing rules. Portable to any look-alike system. The "how an agent must behave", not "how this project works". Project-specific facts belong in `README.md`, not here.
- **No `docs/ISSUES.md`** — this repo has no issue-tracker file. Log findings as grep-able `# TODO` / `# BUG` comments in the relevant file, and report to the operator.
- **No `docs/DEBUG.md`** — for deep scans, read the source first, then `paper.sh` / `auto_trade.py` / `install.sh`.

When a fact fits two files, it belongs in `README.md`. A future agent reading only `README.md` should understand what the project is and how to run it; reading only `AGENTS.md` should understand the rules.

## Doc-audit directives

Docs always reflect the repo — never the reverse. The repo (`.py` source, `install.sh`, `paper.sh`/`live.sh`) is ground truth; every `.md` is a derived description. When a doc and the repo disagree, the doc is wrong — fix the doc in place.

**Missing repo artifacts are deliberate until the operator says otherwise.** A file or directory absent from the repo was removed on purpose — even if a doc references it. Never restore or copy it back; log the gap in a `# TODO` in the code and report to the operator.

**Drift** = a documented fact that disagrees with the executable source (paths, ports, commands, behavior claims). Verify each concrete fact with `grep`.

**Stale** = content that has lost its anchor: paths that no longer exist, claims about transient state ("currently running"). Delete or update.

**Duplicate** = the same fact in two `.md` files. Keep it in exactly one place.

### When to audit

- After every system change, refactor, or operational decision (mandatory per safety rule 4).
- At the end of every task — see "Before finishing a task".
- Before committing any doc-only change.

## Workflow

1. Read `README.md` for the project pitch and layout.
2. Read `AGENTS.md` for the rules.
3. Make changes following the rules.
4. Verify the change works: `python3 -m compileall` (all `.py`), run the tests (`python3 -m unittest discover -s tests`), and smoke-test the launcher (`./paper.sh --help` or equivalent).
5. Update `README.md` only if the pitch, setup flow, usage, layout, or risk-gate defaults changed.
6. Commit and push (safety rule 3). One line per change.

## Before finishing a task

1. Verify the change works using the project's verification commands: `python3 -m compileall -q trading cli tests` and `python3 -m unittest discover -s tests`.
2. **Doc audit — mandatory (safety rule 4).** Walk every `.md` file (`README.md`, `AGENTS.md`):
   - **Delete stale** — outdated paths, transient-state claims, removed references. Confirm every path/port/command still exists or is still valid.
   - **Correct drift** — every fact must match the executable source (`.py`, `install.sh`, launchers). If they disagree, the source wins and the doc is wrong.
   - **Organize duplicates** — each fact lives in exactly one place.
3. **Linting.** Run `python3 -m compileall -q trading cli tests` to catch syntax errors; if a linter (ruff/flake8/mypy) is available in the environment, run it and fix reported issues. Never ship syntax errors.
4. Update `README.md` if the pitch, setup flow, usage, layout, or risk-gate defaults changed.
5. Add new issues as `# TODO` comments in the relevant file and report to the operator.
6. Commit and push. One sentence per change.

## `.md` writing rules

Follow these on every edit to any `.md` file in this repo.

1. **No duplicated content across files.** State each fact once, in the most appropriate file. `README.md` owns project facts; `AGENTS.md` owns agent rules.
2. **No pasting repo file contents.** Don't copy config/compose/Makefile blocks into docs. Describe in prose; link to the file path. Command snippets are fine.
3. **No duplicated prose within a file.** If a paragraph repeats what another section already said, delete one.
4. **Prose over code blocks.** Use a code block only for commands the reader will run, or a structure that genuinely needs monospace (a directory tree, an architecture diagram). Everything else is prose.
5. **One source of truth.** If a detail appears in two files, pick one and delete the other. Prefer the executable source (source code, `install.sh`, config) as truth; docs summarize it.
6. **No runtime snapshots.** Don't write "all three currently running" or "healthy" — it drifts the moment a service stops. Describe steady-state config.
7. **Keep it short.** Every line should answer "would an agent miss this without help?" If not, cut it.
8. **Verify before writing.** Don't describe a path, port, or behaviour you haven't checked in the actual file. Stale docs are worse than missing docs.
9. **Preserve verified useful guidance.** Keep what's accurate and high-signal; only delete fluff, duplicates, stale claims.
10. **Never write volatile, operator-editable state** — statistics, user lists, which app is running, config values changeable from a web UI. Docs describe the setup, not the usage.
11. **No "now removed" / "kept for history" commentary.** Delete dead things and their references instead of describing them.

## Security posture of this repo

Enforced by design, not by the agent:

- **Auto-execute defaults OFF**: `config.yaml` has `trading.auto_execute=false`, `trading.dry_run=true`, `risk.paper_only=true`. Real money requires flipping three flags AND pointing `base_url` at production.
- **All `trading/` tests run with mocked Alpaca**: `tests/test_risk_manager.py` and `tests/test_worker.py` assert gate behavior — **zero API calls, zero orders** can be sent in tests.
- **`config.yaml` is gitignored** (see `.gitignore`): credentials never leave the machine, and `./install.sh` is the only sanctioned writer.
- **Never hand-type secrets into repo files**; always use `./install.sh` so prompts, placeholder rejection, and validation run.
