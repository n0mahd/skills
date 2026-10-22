# Concepts in plain language

Use these explanations when the user, a teammate or a stakeholder needs the idea without the jargon.
Each one is followed by what it means for the code.

## Hexagonal architecture (ports and adapters)

A restaurant kitchen keeps its recipes the same whether orders come from a waiter, a drive-through
or a delivery app, and whichever supplier brings the ingredients. It only needs an order slip in a
standard format.

Software works the same way when it has three parts:

- **The core** holds the rules that make the business what it is ("no more than 10 items per
  order", "discount on Tuesdays"). It knows nothing about websites, databases or vendors.
- **Ports** are the standard sockets the core offers: "give me an order in this shape", "I need
  somewhere to save this". The core defines what it needs, not who supplies it.
- **Adapters** are plug adapters. Each converts something from the outside world to fit a port: a
  web adapter turns clicks into orders, a database adapter turns "save this" into storage.

Things that start work (users, apps, schedulers) sit on one side; things the core relies on to finish
work (storage, payments, email) sit on the other. The hexagon shape means nothing special; Alistair
Cockburn drew it that way to leave room for many ports. "Ports and adapters" is the clearer name.

Why: technology changes faster than business rules. Swapping a vendor means writing one adapter.
Testing means plugging in fakes. The important logic stays readable. The cost is extra structure up
front, which pays off for long-lived software whose surroundings will change.

In code: the core imports nothing from the outside; adapters import the core.

## Dependency injection

Two baristas: one drives to a specific farm whenever she needs milk; the other uses whatever milk
the manager stocks in the fridge. The second can switch to oat milk without retraining. The milk is
the dependency; the manager injects it.

In code: the core never creates its own database connection or payment client. It asks for
"something that can save orders", and a setup step (the composition root) decides which adapter to
hand in: the real database in production, a fake in tests, a console printer in local development.
Hexagonal architecture is the floor plan; dependency injection is how the plugs get connected.

## Interfaces

A job posting: "Delivery driver: must pick up an order, deliver it, confirm arrival." It does not say
car, bike or scooter. Anyone who can do those three things qualifies.

In code: an interface lists what something must be able to do, not how. A port is an interface. The
core writes the job description (`OrderRepository`: save, find by id); adapters are the people who
meet it (the real database, the test fake); dependency injection is the manager who hires one.
Because the core defines the interface rather than the tool, the business logic stays in charge and
the technical details fit around it.

## Fakes, not mocks

A flight simulator versus an instructor with a checklist. The simulator works, simply, and you check
whether you landed. The instructor fails you for touching the flaps before the throttle, even if you
would have landed fine.

- A **fake** is a small real working version: in-memory storage that really saves and finds orders,
  an email outbox you can inspect afterwards.
- A **mock** is a scripted dummy that records calls so the test can assert "save was called once
  with exactly this".

Prefer fakes: tests check results the business cares about, survive refactoring, are reusable across
hundreds of tests, and behave like the real thing. Hexagonal architecture makes fakes easy because
ports are small interfaces and dependency injection makes swapping a one-line choice. Mocks still
fit when the interaction itself is the requirement ("never charge twice") or something is genuinely
hard to fake. The slogan is a strong default, not a ban.

## Domain-driven design

DDD is about what goes inside the hexagon: making the core an accurate picture of the business,
worked out with the people who do the work.

- **Ubiquitous language**: use the business's exact words ("back order", "consignment") in
  conversation, docs and code, so a rule a manager states can be found in the code almost word for
  word.
- **Work with domain experts** continuously, refining the model as understanding grows.
- **Bounded contexts**: the same word means different things in different departments. To sales a
  customer is a deal in progress; to shipping, an address; to billing, a payment method. Give each
  area its own model instead of one giant shared one. Each bounded context can be its own hexagon.
- **Building blocks**: entities keep an identity over time (the same customer after moving house);
  value objects are just values (£10 is £10); aggregates are clusters that enforce their rules
  together; domain events record that something meaningful happened.

DDD is worth its effort where business rules are complicated and important (insurance, logistics,
banking) and usually overkill for an app that mostly stores and shows data.

## How they fit together

- DDD shapes the core: rules, vocabulary, boundaries.
- Hexagonal architecture protects the core from technical detail.
- Interfaces are the core's sockets, named in the business's language.
- Dependency injection plugs adapters into those sockets at one place.
- Fakes let the business rules be tested quickly and realistically.
