# Strategy

Read this before changing anything non-trivial. `<module map path>` says where code is; this page says what the code is for, what must not break, and where it is heading, so a fix lands in the right place and leaves the codebase easier to change next time.

Last reviewed: YYYY-MM-DD.

## Purpose

What the product does, for whom, and what success looks like for that user. One paragraph on the operating context (where it runs, who maintains it, what scale it is built for), since that context explains most of the trade-offs below.

## Priorities

When goals conflict, the earlier one wins.

1. **<Highest>.** One sentence saying what it means in practice.
2. ...

## Invariants

Things that must stay true. Each names what enforces it; "convention" means only review does, so be careful there.

| Invariant | Enforced by |
| --- | --- |
| <must always / must never> | <test file, lint rule, type, or "Convention"> |

## Direction

Where the code is heading. Move toward this when you touch an area, and don't add to what is on its way out.

- **<Target pattern>.** Where it stands today (with numbers), and what new code does instead.
- **Out of the way:** <retired stacks and patterns not to reintroduce>.

## Blast radius

Where a small change reaches far. Before changing the left column, check the right.

| If you change | Also check |
| --- | --- |
| <path or area> | <dependents, tests, docs, operations> |

## Debt register

Ranked by what it costs the next change. Pay an item down when your change already touches its area, and record new debt here rather than leaving it in your head.

1. **<Item>.** Cost today (with numbers), and the next concrete step.

## Open decisions

Questions only the owner can settle. Don't act on them until they do.

- <question> (<link to a decision record if one exists>)

## Keeping the map true

The strategy, the map and the decisions are code: a change that makes them wrong is incomplete.

- Moved, added or removed a module or source directory: update the module map in the same commit. The map test fails on a dead path or an unmapped directory.
- Changed an invariant, a priority or the direction: update this page, and add a decision record when the owner made the call.
- Found debt you are not fixing: add it to the register with its cost and next step.
- Re-read this page when it is more than a month past "Last reviewed", or after a release that changed several areas, and update the date.
