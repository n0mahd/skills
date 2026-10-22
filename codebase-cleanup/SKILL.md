---
name: codebase-cleanup
description: Make a codebase simple and easy for agents to work in, without losing features, looks or behaviour. Two depths. A map pass builds or refreshes the strategic map (strategy page with purpose, priorities, invariants, direction and debt; module map; enforced import boundaries; a test that fails when docs drift). A full cleanup also audits the repo in parallel, removes dead code and duplication, splits oversized files into cohesive modules, gives each concern one home, fixes stale docs and flaky tests, then finishes with the map pass. Use when the user asks to clean up, simplify, tidy, restructure, revamp or "make a codebase agent-friendly"; when a repo has no strategy or architecture docs or they contradict the code; or before a large refactor. For reviewing a single diff use simplify instead.
---

# Codebase cleanup

Leave a repo simpler and easier for an agent to reason about, doing exactly what it did before. Two
goals, in this order: **simplicity** (fewer, clearer files; one way to do each thing; no dead code)
and **legibility for agents** (what the code is for, what must not break, where it is heading, where
everything lives, and checks that keep those facts true). The global "Strategic maintenance" rules
in `~/Knowledge/AGENTS.md` assume the map this skill builds exists.

## Pick the depth

- **Map pass**: the user wants the repo mapped or made agent-friendly, the docs are missing or
  stale, or a refactor is about to start. Survey, fix drift, write the strategy page and module map,
  add guardrails, and do only small mechanical moves. Big splits and dedup go in the debt register.
- **Full cleanup**: the user asks to clean up, simplify or restructure. Everything in phases 0-6
  below, ending with the map pass. If unsure, do the map pass and offer the full cleanup with the
  debt register as its plan.

Behaviour, HTTP contracts, schemas, prompts, visible text and looks never change in either depth.
Anything a user or API client could notice is a finding for the owner, not a cleanup.

## Outcome

End with one of these and say which:

- **cleaned**: a pushed branch of small, single-topic commits; tests at least as green as the
  baseline; the map built or refreshed with guardrails passing.
- **built** / **refreshed**: (map pass) the map now exists or its drift is fixed; guardrails pass.
- **clean**: the map was accurate, the guardrails pass, and nothing was worth changing.

The report says: what changed by area, bugs fixed and how each was proven, verification against
the baseline, owner decisions with a recommendation each, changes proposed but not made (and why),
and leftovers (worktrees, debt). Never merge or deploy without asking.

## Phase 0: set up and survey

1. Read the repo's agent docs (`AGENTS.md`, `CLAUDE.md`, `documents/`, ADRs) and the user's memory
   notes (`grep -ril <project> ~/Knowledge/memory`): ops facts, shared-checkout rules, production
   quirks. Contradictions between docs and code are findings.
2. Check for in-flight work before moving files (`git worktree list`, `git branch --no-merged main`,
   recent commits on `origin/main`). Moves under someone's open branch cost them merge conflicts.
3. Work in **your own worktree from `origin/<main>`** on a new branch, never in a shared checkout.
   Install dependencies from the lockfile (`npm ci`).
4. **Baseline every test layer before changing anything**, output saved to a file: lint, types,
   build, unit, integration, E2E. Run flaky suites 3-4 times and record each failure as always or
   sometimes. Without this no failure can be called a regression.
5. Measure, so claims are grounded:
   - Shape: source directories, file counts, largest files
     (`git ls-files | xargs wc -l | sort -n | tail -30`).
   - Churn: `git log --since=90.days --name-only --format= | sort | uniq -c | sort -rn | head -30`.
   - Dependency direction: which layers import which; look for inversions.
   - Gates: what CI or the deploy actually runs, and how it gets the code (a `git archive` copy has
     no `.git`, so a check that shells out to git fails there).
   - Invariants from docs, tests and memory, each with what enforces it, or "convention".
6. Pick dev-only ports and a dev-only database for yourself, and different ones per sub-agent.

## Phase 1: audit in parallel (full cleanup; read-only)

Split the repo into 2-4 areas with no shared files (e.g. backend, frontend logic, styles + markup +
docs + scripts + tests) and give each a read-only audit agent from `references/briefs.md`. Demand
evidence for every claim (a repo-wide grep proving "unused", both copies of a "duplicate"), a
value/risk order and a word cap. Meanwhile read the entry points and the central dispatcher yourself;
you need your own model of the code to judge the findings.

Triage into **do** (behaviour-preserving: dead code, duplication, moves, splits, names, stale
comments and docs, flaky tests), **fix as a bug** (clear defects users hit; small separate commits,
each proven by a check that fails before and passes after) and **ask the owner** (behaviour, API,
visible text, data, security, production config including env var names production reads). Security
findings in a public repo go to the private findings register, not repo docs.

## Phase 2: plan the structure

Score the repo against the legibility checks below and rank changes by payoff for the next agent
against churn and risk.

- For each oversized file, design the split before moving anything: cohesive modules, a one-line
  purpose each, and **a one-way dependency order**. `scripts/split_blocks.py check` fails on cycles;
  in CommonJS a cycle with destructured imports gives `undefined` at load time.
- Decide each concern's single home (auth/tokens, lookups, transactions, error handling, config and
  env reads, broadcasting). A parameter threaded through every call (a socket server, a client) can
  often become one module with a setter.
- Keep public entry points stable, and make them real indexes that document the layers.
- Never a ground-up rewrite of working production code without the owner's sign-off on a written plan.

## Phase 3: execute

Own the riskiest area (usually the core domain). Give the others to implementer sub-agents in
**their own worktrees branched from yours**, with disjoint file scopes, their own ports, the
baseline failure list and the repo's special rules (template in `references/briefs.md`). Shared docs
stay yours; implementers report doc changes instead of making them.

- **Pure moves first, as their own commit**: `split_blocks.py split` then `verify` proves every moved
  block byte-identical. Rewrite imports with a script, not by hand. Refine in later commits.
- **One topic per commit**, message says why. Fast checks after every step, full suite per area.
- After extracting a helper, grep the target files for locals of the same name (shadowing gives
  "Cannot access X before initialization"). Keep imports at the top; one below its first use fails.
- Scripted multi-file edits: assert each pattern before writing; after a failure, check which files
  were already written before rerunning.
- **Never `git checkout`/`reset` a file with uncommitted work** to undo an experiment. Probe on a copy
  or commit first.
- No-bundler frontends: check for duplicate top-level names across every script a page loads, and
  bump cache keys (`?v=`) on every page for each changed asset, above any key `main` has used.
- CSS and UI: full-page screenshots before and after each commit at several widths and key states,
  pixel-diffed. Every difference is explained.
- Fix flaky tests as soon as one costs you a rerun: pin the randomness (fixed dice, seeded ids),
  never add sleeps. Investigate "known" failures; they are often test-runner setup (missing keys,
  ports) and cheap to fix.
- Deploy pipelines, systemd units and production config are operations: propose changes as owner
  decisions.

## Phase 4: integrate and review

Merge each implementer branch into yours and review it before trusting it: read the diff of the
risky parts, run the name-clash and import checks, then the **whole** gate (static checks, unit,
integration, E2E, long scenarios). Keep raw logs in a file and filter only for display; a `grep`
that matches nothing hides the result and fails the command.

## Phase 5: the map and its guardrails (both depths)

Few artifacts, one job each, in the repo's existing places (don't add a second `ARCHITECTURE.md`).

1. **`AGENTS.md` "Orient first" block**: read the strategy and map before a non-trivial change, place
   the change, update both in the same commit when a module, invariant or direction moves.
   `CLAUDE.md` imports `AGENTS.md` (`@AGENTS.md`) rather than repeating it.
2. **Strategy page** (`documents/strategy.md` or equivalent) from `templates/strategy.md`: purpose,
   ranked priorities, invariants with what enforces each, direction, blast radius, a ranked debt
   register with real numbers, open owner decisions, how the map is kept true. Every claim cites
   evidence; priorities and direction belong to the owner, so ungrounded ones go under Open decisions.
3. **Module map** (`documents/architecture.md`, or a "Code map" section in `AGENTS.md` for small
   repos): a "Start here" table (task → entry files), one entry per source directory (runtime, what
   it owns), the layer order and import boundaries, and the rules agents must keep.
4. **Guardrails**, each proven to fail on a violation (a fake path in a doc, a probe import across a
   boundary) before trusting it passes:
   - A map test (adapt `templates/architecture-map.test.ts`, or extend the repo's existing check
     script): every path a living doc names exists, every source directory is in the map, the
     strategy page keeps its sections.
   - Boundary rules in the linter (ESLint `no-restricted-imports`, import-linter, `depguard`, or the
     repo's own check) for every "X never imports Y" the map claims.
   - Both run where merges are gated.
5. One home per fact: player/product rules in one doc, setup in one, ops in one; the rest link.
   Historical changelogs become a short list of what's still open; git keeps the history.
6. **Cold-agent check**: give a fresh read-only sub-agent a realistic backlog task and only "plan it,
   cite files". It should find the owning module, the invariants and the blast radius from the docs
   alone; where it can't, the map has a gap.
7. Record durable facts (production gotchas, findings, fixed debt) in memory.

## Phase 6: verify and ship

Lint (zero errors), types, build, the full test gate in the same form CI or the deploy runs it, the
map test, the cold-agent check. Push the branch, not main: map and guardrails in their own commit,
moves and cleanups in theirs, so each can be reviewed or reverted alone. Report per "Outcome"; offer
the merge path (`privacy-check`, PR, rollout) without taking it.

## Legibility checks

A codebase is easy for an agent when:

- **Names predict location.** A directory's name says what is in it and where it runs; a feature
  keeps one name across layers, so one `rg <feature>` finds all of it.
- **Dependencies point one way**, enforced by a check, not just the docs.
- **Each concept has one home.** One API client, one config reader, one gateway per service. A
  second way of doing something is debt.
- **Entry points are obvious.** Every "Start here" task leads to at most three files.
- **Files fit in context.** About 500 lines is a smell, 800+ is debt, unless it is data or a test.
- **Docs are few, current and checked.** One doc per job; the map test guards the paths.
- **Invariants are executable.** Each "must never" has a test, type or lint rule; convention-only
  ones are listed as debt.
- **The gate is honest.** What a merge must pass is what the docs say it must pass.

## Good runs and bad runs

Good runs:
- Baseline first, so every red test is classified as pre-existing, flaky or new.
- Evidence-backed audits before any edit; the plan comes from findings, not taste.
- Mechanical moves done by script and proven identical; behaviour edits separate and small.
- Parallel work in separate worktrees with disjoint files and ports, then reviewed and fully
  re-tested after merging.
- Behaviour changes surfaced to the owner with a recommendation, not slipped in.
- Guardrails left behind (drift check, boundary check, cache-key check), so it stays clean.

Bad runs:
- Editing a shared checkout, or starting without a baseline.
- Big-bang rewrites, or moves mixed with logic changes in one commit.
- Trusting a sub-agent's "all passing" without merging, reviewing and re-running.
- "Cleaning up" visible text, API shapes, env var names or security-relevant behaviour.
- Accepting flaky or "known" failures that hide real regressions.
- Docs left describing the old layout: a stale map is worse than none.
- Losing uncommitted work to a careless `git checkout` or `reset`.

## Files

- `scripts/split_blocks.py`: outline, dependency graph, cycle check, generated split and
  byte-identity verify for large JS/TS files (CommonJS or ESM). Run `outline` first; any LOOSE line
  means the file doesn't fit the column-0 shape and needs hand care.
- `references/briefs.md`: audit-agent and implementer-agent briefs.
- `templates/strategy.md`: the strategy page.
- `templates/architecture-map.test.ts`: the map/drift test to adapt.
