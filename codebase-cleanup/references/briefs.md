# Briefs for codebase-cleanup sub-agents

Fill the `<...>` parts. Each brief stands alone: the agent starts cold.

## Read-only audit agent (one per area)

```
You are auditing (read-only, very thorough) <AREA> of the repo at <WORKTREE PATH> (<one-line
description of the stack>). Read <AGENTS.md / docs> first for the architecture rules. Scope:
<directories/files>; skip node_modules. You are the implementer of this audit, do not delegate.

Goal: the owner wants the codebase cleaned up for (1) simplicity of code, files and architecture
and (2) readability for AI agents, WITHOUT losing any features, behaviour, looks or API. Produce a
concrete, prioritized findings list. For each: file:line, what it is, the proposed change, and
evidence (a grep across the WHOLE repo incl. tests/scripts/HTML showing something is unused, or the
duplicated snippets side by side). Hunt for:
- Dead weight (catalogue and proof rules in <SKILL DIR>/references/dead-weight.md; read it first):
  unused exports/functions/files/deps/env vars/CSS selectors; functions that do nothing (empty,
  pass-through, return the input); functions only tests call, with their tests; unused fixtures,
  fakes and mocks; empty folders and empty files; commented-out code; stale suppressions; flags
  fully rolled out; compat shims for removed features; unreachable branches; docs, comments,
  config, CI, ignore files and env examples naming things that no longer exist. Leads:
  `<SKILL DIR>/scripts/dead_weight.py <REPO>`. Check dynamic reach (string-built names,
  registries, config-named handlers, entry points) and callers outside the repo before claiming.
  For each removal, list the whole chain that goes with it.
- Duplication: the same helper or query in several files; propose its single home.
- Indirection that adds nothing: re-export files, one-caller wrappers, params threaded everywhere.
- Oversized files: propose a split into cohesive modules (names per module, cross-dependencies,
  a load/import order without cycles), or argue to keep it.
- Inconsistent patterns: two ways of doing one thing (errors, validation, transactions, config).
- Stale or contradictory docs and comments; every path a doc names must exist.
- Tests that can't fail, flaky tests, tests named after dates instead of features.
- Real bugs you notice: list them separately at the top.
Mark anything whose fix would change behaviour, visible text or security as "needs owner decision".
Be precise; don't pad. Report in under ~1500 words, ordered by value/risk (high value, low risk first).
```

## Implementer agent (one per area, own worktree)

```
You are the implementer of this task: write the code yourself and do not delegate it further.

# Goal
<Area> cleanup for <repo>: (1) simplicity, (2) readability for AI agents. Do NOT lose any feature,
capability, look or behaviour. Fixing the bugs listed below is in scope.

# Where
- Your worktree: <PATH> (branch <BRANCH>). Work and commit ONLY there; dependencies are installed.
  Never touch the shared checkout, other worktrees, or production.
- Read <AGENTS.md / design docs> first.
- Scope: <files/dirs you may edit>. Out of scope (others own them): <list>. If a doc or out-of-scope
  file needs a change because of yours, list it in your final report instead.

# Repo-specific rules
<cache keys / no-build constraints / globals shared across scripts / design tokens / ports>

# Work list (from a read-only audit; verify each claim before acting, skip any that is wrong)
<paste the triaged findings for this area, grouped: bugs (each its own commit), dead code,
duplication, structure/splits with the risks the audit named>
Do NOT change: <behaviour-changing items the owner must decide>.

# Verification (required)
- After each step: <fast checks>.
- Full suite on YOUR ports: <command with dev-only ports and db path>. Never use <prod ports>.
- Baseline before your changes: <counts>, known failures <names> (<always/flaky>). Your final run
  may have no other failures. Investigate new failures; don't weaken tests.
- <Visual check: screenshots before/after at <widths> and pixel diff, for UI/CSS work.>
- Leave no servers or browsers running; keep test workers at <N> or fewer.

# Commits
Small, focused, message explains why, each ending with:
Co-Authored-By: <model attribution line>
Do not push, merge, rebase onto other branches, or deploy.

# Final report
Commits (hash + subject); bugs fixed and how each was verified; items skipped or changed and why;
doc updates needed outside your scope; final test result lines.
```
