# Strategic coding in a hexagonal codebase

Read this only when the repo uses ports and adapters (or is migrating to them): an architecture
doc says so, or the tree has a core or domain package with ports, an adapters or infrastructure
package, a composition root and a boundary check. It maps the strategic-coding loop onto that
structure. Don't load the `hexagonal-architecture` skill for routine work; the triggers for that
are under "When to hand off" below.

## Place the work

- **Which bounded context** owns the concept? Use its words (the ubiquitous language) for every
  new name. A word that means something different in another context stays there.
- **Which use case** (driving port) is the entry point, and which **driven ports** does it touch?
- **Existing guards**: the boundary check (core never imports infrastructure), the contract suite
  for each port, and the fakes. These are the invariants this structure enforces; know how to run
  them before changing anything.

## Where the change belongs

The concept's home depends on the kind of rule:

| The change is about | Its home |
| --- | --- |
| A business rule, limit, state transition or validation beyond shape | Entity or value object in the core |
| Orchestration of a use case (load, decide, save, publish) | Application service behind the driving port |
| Translating external shapes (requests, rows, payloads, vendor quirks) | The adapter, at the boundary |
| Which adapter is used where | The composition root, and nowhere else |
| A pure screen or report query | A query port returning DTOs; it may skip the domain |

A business rule found in a controller, repository or SQL query is in the wrong place: moving it
into the core is the "at the home" level of the change.

## The levels, in hexagonal terms

1. **Local**: an adapter-only change (a mapping, a new field in a translation, a vendor quirk).
   Fine when the rule really is about the outside world.
2. **At the home**: the rule goes into the domain model or application service, tested through the
   driving port with fakes.
3. **For the class**: a value object that makes invalid states unrepresentable, a new case in a
   port's contract suite so every adapter (and the fake) is held to it, or a tighter boundary rule.
4. **Design**: a new port, splitting or merging ports, a new bounded context, an anti-corruption
   layer, or moving a slice behind ports. Hand off (see below).

Reuse an existing port before adding one; widen a port only when the use case needs it. Don't
over-port: a port goes where the core meets something it shouldn't know about, or something that
makes tests slow or nondeterministic.

## Features

A new use case is a slice: name it in domain language, put rules in the domain model, declare only
the driven ports it needs, write the fakes and contract cases for any new port, write the adapter,
wire it in the composition root, keep the boundary check green. The `hexagonal-architecture`
skill's "slice loop" is the full checklist; read that section of its `SKILL.md` for a new use case
rather than the whole skill.

## Fixes

Find which layer the defect lives in, then test it there:

- **Domain rule wrong**: reproduce with a use-case test through the driving port, with fakes.
- **Adapter translation wrong**: reproduce with an adapter or contract test against the real thing.
- **Fake drifted from the real adapter** (tests pass, production fails): add the missing case to
  the port's contract suite so it runs against both, then fix whichever side is wrong. This is the
  class-level fix for a whole family of "passes in tests" bugs.
- **Wiring wrong**: fix it in the composition root, and add a startup or smoke test if cheap.

## In a partly migrated codebase

The direction is "toward ports and adapters", but a bug fix is not a migration.

- In an unmigrated area, make the change in the current style unless this area is the next slice
  on the plan. Record the area in the debt register.
- One small step is allowed when it is what makes the change correct or testable: injecting a
  `Clock` or ID generator, or extracting a single port with a fake. Commit it separately, first.
- Never add a new infrastructure import to the core "just this once", and never add a second
  composition root.

## Traps

- Business rules leaking into controllers, repositories, queries or the frontend.
- Ports named after technology (`StripeClient`) instead of the need (`PaymentGateway`).
- Mocking internal collaborators where a fake exists; asserting call sequences instead of outcomes.
- Changing a fake without adding the matching contract case, or changing an adapter without
  running the contract suite against it.
- Domain objects returned straight out as API responses, or request objects passed into the core.

## When to hand off

Load the `hexagonal-architecture` skill only when the chosen level is **design**, when the user
asks to assess or migrate, or when the codebase has no ports yet and the strategic note would
recommend introducing them. Even then, read just the sections you need from its
`references/implementation.md` (layout, fakes, contract tests, boundary enforcement or migration
recipes) rather than the whole file.

## Add to the strategic note

The bounded context touched, the ports added or changed, and the boundary check and contract
suite results.
