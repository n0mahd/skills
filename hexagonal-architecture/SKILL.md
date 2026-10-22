---
name: hexagonal-architecture
description: Design, assess or migrate a codebase to hexagonal architecture (ports and adapters) with domain-driven design, dependency injection at a composition root, interface-defined ports owned by the core, and fakes rather than mocks for tests. Use when the user asks to apply hexagonal architecture, ports and adapters, clean or onion architecture, to decouple business logic from frameworks, databases or vendors, to make a codebase easier to test or swap infrastructure, or invokes /hexagonal-architecture. Do not trigger for a small script, a one-off bug fix, or a review of a single diff with no architectural question.
---

# Hexagonal architecture

Keep the business rules in a core that knows nothing about frameworks, databases, queues, HTTP or
vendors. The core states what it needs through ports (interfaces it owns, named in the business's
language). Adapters on the outside fulfil those ports. A single composition root wires real adapters
in production and fakes in tests. Behaviour never changes as a side effect of restructuring.

## The model in five rules

1. **Dependencies point inward.** Adapters import the core. The core never imports an adapter, a
   framework, an ORM, an HTTP client or an SDK. This is the one rule everything else serves.
2. **The core owns its ports.** Ports are interfaces declared inside the core, shaped by what the
   use case needs, named in domain language (`OrderRepository`, `PaymentGateway`, `Clock`), never by
   technology (`PostgresOrderDao`, `StripeClient`).
3. **Two kinds of port.** Driving (inbound) ports are the use cases the outside world calls: an
   application service or command handler. Driven (outbound) ports are what the core calls out to:
   storage, payments, email, time, randomness, IDs.
4. **Wire at one composition root.** Dependency injection by constructor. No service locators,
   globals or `new SomeAdapter()` inside the core. The composition root (`main`, app factory,
   container config) is the only place that knows which adapters exist.
5. **Fakes, not mocks.** Every driven port gets a small working in-memory fake that lives with the
   tests. Use cases are tested through the driving port with fakes plugged in, asserting outcomes
   (state, returned values, emitted events), not call sequences. A shared contract test suite runs
   against both the fake and the real adapter so the fake cannot drift.

Domain-driven design shapes what is inside the core: the ubiquitous language, entities, value
objects, aggregates and domain events, split into bounded contexts. Each bounded context is its own
hexagon with its own ports. Read [references/concepts.md](references/concepts.md) when the user or a
teammate needs the plain-language explanation, or when a design decision hinges on one of these
ideas.

## Pick the mode

- **Assess**: the user wants to know how far a codebase is from hexagonal, or where to start. Map
  it, report violations ranked by cost, propose the first slice. Change nothing.
- **Greenfield**: a new service or module. Lay out the structure, write the first use case end to end
  with its ports, fakes, a real adapter, contract tests and the boundary check.
- **Migrate**: an existing codebase. Move one vertical slice at a time behind ports (strangler style),
  keeping every test green after each step. Never a big-bang rewrite.

If unsure, run Assess and offer Migrate with the assessment as its plan.

## Before any change

- Read the repo's own docs (README, CLAUDE.md, AGENTS.md, ARCHITECTURE.md, ADRs) and follow them
  where they conflict with this skill; note the conflict in the report.
- Detect the language, framework, test runner and existing DI style. Adopt the idioms of that stack
  (Python protocols or ABCs, TypeScript interfaces, Go interfaces declared by the consumer, Java or
  C# interfaces, Rust traits). Do not add a DI container if constructor injection suffices.
- Record a baseline: the full test command and its result. Every later step must be at least as
  green.
- Check scale. For a small CRUD app with little business logic, say that hexagonal is probably more
  structure than it needs and propose the lighter subset (a domain module, ports for the database
  and external services, fakes in tests) unless the user insists.

## Assess

1. Find where business rules live today. Search for the decisions the business cares about
   (pricing, eligibility, state transitions, limits, validation beyond shape).
2. List every place the core-to-be imports infrastructure: ORM models used as domain objects,
   framework request objects passed into logic, SDK calls inside services, `datetime.now()`,
   `Math.random()`, environment reads, direct HTTP calls.
3. Identify candidate bounded contexts: clusters of code that share vocabulary, and words that mean
   different things in different places (the "customer" problem).
4. Check how tests work: count mocks of internal collaborators versus real fakes, and whether tests
   need a database, network or framework to exercise a business rule.
5. Report: a one-paragraph verdict, a context map, the violations ranked by how much they block
   testing or change, and a proposed first slice (a use case with high business value and few
   collaborators).

## Greenfield and migrate: the slice loop

Work one use case at a time. For each slice:

1. **Name it in domain language.** Agree the use case name and its inputs and outputs with the
   user's vocabulary (`PlaceOrder`, `ApproveClaim`), not CRUD verbs, unless the domain really is CRUD.
2. **Extract or write the domain model.** Entities with identity, immutable value objects, invariants
   enforced in constructors and methods. No framework annotations or ORM base classes in the domain
   if the language allows keeping them out; if the team already accepts them, flag it rather than
   fight it.
3. **Declare the driven ports** the use case needs, in the core, shaped by the use case. Keep them
   small. Include `Clock` and ID generation when the logic depends on time or new identifiers.
4. **Write the application service** behind a driving port. It orchestrates domain objects and
   driven ports, and contains no infrastructure.
5. **Write fakes** for each new driven port in the test tree, plus a contract test suite for each
   port (see the reference). Write use case tests against the driving port with fakes.
6. **Write or move the real adapters**: the ORM or SQL repository, the vendor client wrapper, the
   HTTP controller or CLI or queue consumer that calls the driving port. Translate at the boundary:
   adapters map between external shapes (DTOs, rows, payloads) and domain objects. Domain objects do
   not leak out as API responses, and request objects do not leak in.
7. **Run the contract suite against the real adapter** (integration tests, may need a container or
   test database; mark them so they can run separately).
8. **Wire it** in the composition root. In Migrate mode, route the old entry point to the new use
   case and delete the old path only once tests prove equivalence.
9. **Enforce the boundary** with an automated check that fails on a core-to-infrastructure import
   (tool options per language in the reference). Add it in the first slice, not at the end.
10. **Commit** the slice on its own: one topic, tests green, boundary check green.

Read [references/implementation.md](references/implementation.md) for the directory layout, code
patterns in several languages, the fake and contract-test patterns, boundary-check tooling, and the
migration recipes.

## Judgement calls

- **Do not over-port.** A port for every class is noise. Ports go where the core meets something it
  should not know about, or something that makes tests slow or nondeterministic.
- **Read models may skip the domain.** Pure queries for screens or reports can go from a driving
  adapter straight to a query port returning DTOs; the aggregates are for enforcing rules on writes.
- **Mocks are allowed** when the interaction is itself the requirement (exactly once, never twice,
  ordering guarantees to a third party) or a fake would be unreasonably complex. Say why in the test.
- **Shared kernel stays tiny.** Types shared across bounded contexts (money, IDs) live in one small
  module both depend on. Contexts talk through ports, events or an anti-corruption layer, not by
  importing each other's internals.
- **Transactions** belong to a unit-of-work port or the application service boundary, not to the
  domain.

## Done means

- Tests at least as green as the baseline; new use cases tested through driving ports with fakes.
- Each driven port has a fake and a contract suite that runs against the fake and the real adapter.
- The boundary check runs in the normal test or lint command and passes.
- A short architecture note exists or is updated (ARCHITECTURE.md or the repo's equivalent): the
  contexts, the ports per context, where adapters and the composition root live, how to add a slice,
  and how to run the contract and boundary checks.
- No behaviour, API contract, schema or visible text changed unless the user asked for it.

## Report

Say which mode ran. Then: what changed by context and slice, the ports introduced, the boundary
check and how to run it, test results against the baseline, judgement calls made and why, what
remains (with the next recommended slice), and anything that needs the owner's decision. Never
merge or deploy without asking.
