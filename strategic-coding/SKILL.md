---
name: strategic-coding
description: Approach every coding task (feature, bug fix, refactor, failing test, config change, review comment, incident follow-up) strategically. Place the work in the system before touching code, understand the real need or root cause behind the request, find related code and repeated patterns, choose the level of the change on purpose, check it moves the codebase toward its direction rather than away from it, and leave the system easier to change and harder to break, without letting the task balloon. Use for any non-trivial change in an existing codebase, when the user says "do this properly", "think about the bigger picture", "how does this fit", "root cause", "don't just patch it", "why does this keep happening", or invokes /strategic-coding. Do not trigger for a whole-repo cleanup (use codebase-cleanup) or an architecture migration (use hexagonal-architecture).
---

# Strategic coding

Every tactical change is also a small decision about where the codebase goes. Do the task in front
of you completely, and make sure the way you do it fits the system's purpose, invariants and
direction, addresses the real need or cause rather than the surface request, and leaves the next
person (or agent) better placed. Strategy here means **judgement about fit and consequences**, not
a bigger diff: the best strategic change is often a smaller one in a better place.

This applies to all kinds of work:

- **Features**: build on the existing concepts and homes, extend rather than duplicate, and shape
  the change so the next feature in the same direction is easy.
- **Fixes**: remove the cause rather than the symptom, and stop the same class of mistake recurring.
- **Refactors**: move toward the stated direction, in steps that keep behaviour and stay reviewable.
- **Config, dependencies and ops changes**: find every place the value or assumption lives, and
  what depends on it.

## Scale the effort to the task

Run the loop below at the depth the task deserves and say which you chose:

- **Glance** (typo, copy change, obvious one-liner): a minute on steps 1 and 2. Is this the right
  place, and does the same thing exist next door?
- **Standard** (most features, bugs and small refactors): the whole loop, briefly. A few searches,
  a short strategic note in the report.
- **Deep** (new concept or module, recurring bug, incident, data at risk, a change that crosses
  modules or alters a contract): the whole loop with evidence, related code enumerated, options
  written down, and owner decisions surfaced before acting.

Escalate a level when you find a surprise (the cause is elsewhere, the pattern repeats, an
invariant is involved, the feature overlaps an existing one). Never let the strategic work replace
doing the actual task.

## The loop

### 1. Place the work

Before editing, build a one-paragraph picture of where this sits:

- **Purpose**: what the user or system is trying to achieve, and what "done" means to them (not
  just "the test passes" or "the button exists").
- **Map**: read the repo's strategy and architecture docs if they exist (`AGENTS.md`, `CLAUDE.md`,
  `documents/strategy.md`, `ARCHITECTURE.md`, ADRs). Note the priorities, the invariants that touch
  this area, the stated direction, the blast-radius table and the debt register. If there is no
  map, infer the essentials from the code (entry points, who calls this, layer order) and say the
  map is missing. If the repo uses ports and adapters (hexagonal architecture), also read
  [references/hexagonal.md](references/hexagonal.md).
- **Home**: which module owns the concept involved (auth, config, money, dates, retries,
  validation, a domain entity). New code and fixes belong there, not wherever was convenient to
  reach.
- **History**: `git log -p -- <file>` and `git blame` on the code involved. Was this tried, fixed
  or reverted before? Is there an issue, ADR or comment explaining why it is the way it is? A
  "weird" line is often load-bearing.

### 2. Understand the need, then what is related

- **For a fix, reproduce first** with the smallest check that fails (a test where possible). No
  reproduction means you are guessing; say so. Then ask **"why was this possible?"** until you
  reach something the code could have prevented: a missing invariant, an ambiguous name, a
  duplicated concept, an unchecked boundary, a type that admits invalid states, a missing test
  layer. Stop when the next "why" leaves the codebase and report that level.
- **For a feature or change, find the need behind the request.** What problem does it solve, and
  is the requested shape the best way to solve it here? If the request conflicts with an invariant
  or the direction, or a simpler route meets the same need, raise it before building.
- **Look for related code.** Search for existing implementations of the same concept, similar
  features, the same idiom or copied block (`rg` the names, the calls, the domain words). For a
  bug, one instance is a bug and three is a class. For a feature, an existing near-match is the
  thing to extend. Record what you find with paths.

### 3. Choose the level of the change on purpose

List the options from lowest to highest and pick deliberately:

1. **Local**: change only where the request surfaced (a guard, a branch, a new component beside
   the old one).
2. **At the home**: change the module that owns the concept, so every user of it benefits.
3. **For the class**: make the mistake impossible or the next similar change trivial everywhere (a
   type, a constructor invariant, a shared helper replacing copies, a lint rule, a contract test,
   an extension point).
4. **Design**: the need exposes a structural problem (wrong boundary, wrong ownership, missing
   abstraction).

Default to **the lowest level that meets the real need at its home**, plus the cheapest guard that
stops a class of bug recurring. Go higher only when scope allows and the payoff is clear;
otherwise propose it. A purely local change is fine when it is the honest fit (a one-off, or a
labelled stopgap for an incident or frozen code), with any real fix recorded as debt. Don't build
an abstraction for a single use: wait for the second or third.

Test each candidate against the system:

- **Direction**: does it move toward the stated direction, or add to a pattern that is on its way
  out? Use the pattern the codebase is migrating to, in the area you touch.
- **One home**: does it reuse the existing way of doing this, or introduce a second one? A second
  way is debt, even if it is nicer.
- **Invariants and priorities**: does it keep every invariant? When priorities conflict, does it
  favour the one the strategy ranks higher?
- **Blast radius**: who else calls this, and what changes for them (callers, API clients, stored
  data, jobs, caches, other services, deploy order, rollback)? A change that is right locally and
  wrong for a caller is not done.
- **Next change**: will the next feature or fix in this direction be easier or harder after this?
- **Reversibility**: prefer the option that is easy to undo when evidence is thin.

### 4. Implement within scope

- Keep the behaviour change and any structural change in **separate commits** (or clearly separate
  hunks if the repo squashes), so each can be reviewed and reverted alone. Preparatory refactors go
  first: make the change easy, then make the easy change.
- Fix related instances in the same change only when they are the same mechanical edit, low risk
  and inside the area you were asked to touch. Otherwise list them.
- Anything a user, API client or operator could notice beyond the intended change (behaviour,
  contract, schema, visible text, config, security posture) is an **owner decision**: ask, with a
  recommendation, before doing it.
- Don't refactor on the way past unless the refactor is what makes the change correct or simple.
  Note the urge in the debt list instead.

### 5. Leave the system better placed

- **Tests at the layer where the behaviour lives.** For a fix, a regression test that fails before
  and passes after; run it both ways. For a feature, tests that pin the behaviour the user relies
  on, not the implementation.
- **The cheapest guard** for any class of mistake you found: a type, an assertion at a boundary, a
  lint rule, a contract test. A guard you can't add now goes in the debt register.
- **Keep the map true**: if the change added a module or concept, moved ownership, changed an
  invariant, the direction or the blast radius, update the strategy or architecture doc in the same
  change. Add related work you didn't do and any stopgaps to the debt register (or the repo's
  equivalent) with cost and next step.
- Leave a comment only where the code alone can't explain *why* (a non-obvious constraint), with a
  link to the issue or decision.

### 6. Report the strategic note

Alongside the usual summary, give a short strategic note:

- **Depth** run (glance, standard, deep).
- **Need or root cause** in one sentence (for a fix, where the "why" chain stopped).
- **Level chosen** and why; the higher options considered and not taken.
- **Related code**: changed (where) and left (where, with a recommendation).
- **Fit**: how the change relates to the direction, invariants and blast radius; any doc updated.
- **Tests and guards** added, and how each was proven.
- **Owner decisions** needed, each with a recommendation.

Keep it proportionate: three lines for a standard task is fine.

## Traps

- **Tunnel vision**: making the failing test pass by changing the test, widening a type to `any`,
  catching and ignoring, or special-casing the input from the report.
- **The second way**: a new helper, client, component or config read next to the existing one
  because it was quicker than understanding it.
- **Workaround layering**: code that compensates for an earlier workaround. Find and remove the
  first one, or record it.
- **Building the literal request**: shipping exactly what was asked when it duplicates an existing
  feature or fights the direction, without saying so.
- **Speculative architecture**: abstractions, flags and extension points for needs nobody has yet.
- **Strategy as scope creep**: a small task that arrives with a rewrite. Strategic thinking is
  mostly about *where* and *what else*, and often ends in a note, not more code.
- **Changing it where it surfaced**: guarding the call site that noticed a problem, or adding a
  feature in the screen that asked for it, instead of the module that owns the concept.
- **Silent behaviour change** for other callers, hidden in an unrelated change.
- **Unrecorded knowledge**: finding the real cause, the related code or the debt and leaving it
  only in the chat.

## Files

- [references/questions.md](references/questions.md): question bank per step, worked examples for
  features, fixes and config changes, and a template for the strategic note. Read it for deep runs
  or when unsure which level fits.
- [references/hexagonal.md](references/hexagonal.md): the loop mapped onto ports and adapters:
  where each kind of change belongs, the levels in hexagonal terms, fixes by layer, partly
  migrated codebases, and when to hand off to `hexagonal-architecture`. Read it only when the repo
  is hexagonal or moving there.

Related skills: `codebase-cleanup` builds the strategy page and module map this skill reads;
`hexagonal-architecture` takes over when the right level is a new port, a new bounded context or
migrating a slice.
