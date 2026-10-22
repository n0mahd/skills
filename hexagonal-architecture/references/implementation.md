# Implementation guide

Patterns for laying out, wiring, testing and enforcing a hexagonal codebase. Adapt names and layout
to the repo's language and existing conventions; the dependency rule is what matters, not the folder
names.

## Layout

One hexagon per bounded context. A typical shape:

```text
src/
  shared_kernel/            # tiny: Money, ids, Result types. No infrastructure.
  ordering/                 # one bounded context = one hexagon
    domain/                 # entities, value objects, aggregates, domain events, domain errors
    application/            # use cases (driving ports + their implementations)
    ports/                  # driven ports: OrderRepository, PaymentGateway, Clock, ...
    adapters/
      inbound/              # http controllers, CLI, queue consumers -> call use cases
      outbound/             # postgres repo, stripe gateway, smtp mailer -> implement ports
  billing/
    ...
  bootstrap/                # composition root: builds adapters, injects into use cases
tests/
  ordering/
    fakes/                  # in-memory fakes for each driven port
    contracts/              # port contract suites, run against fake AND real adapter
    use_cases/              # tests through driving ports, with fakes
    integration/            # real adapters (marked, may need containers)
```

Allowed imports:

| From \ To            | domain | application | ports | adapters | frameworks / SDKs |
|----------------------|:------:|:-----------:|:-----:|:--------:|:-----------------:|
| domain               |   yes  |     no      |  no   |    no    |        no         |
| application          |   yes  |     yes     |  yes  |    no    |        no         |
| ports                |   yes  |     no      |  yes  |    no    |        no         |
| adapters             |   yes  |     yes     |  yes  |   yes    |        yes        |
| bootstrap            |   yes  |     yes     |  yes  |   yes    |        yes        |

Contexts import each other only through a published API (use cases, events or an anti-corruption
adapter), never each other's `domain/`.

Placing driven ports in `ports/` or inside `application/` are both fine; pick one and keep it
consistent. In Go, idiomatically declare the interface in the consuming package (the application).

## Code shape (Python)

```python
# ordering/domain/order.py
from dataclasses import dataclass, field
from shared_kernel.money import Money

class OrderLimitExceeded(Exception): ...

@dataclass(frozen=True)
class OrderLine:
    sku: str
    quantity: int
    unit_price: Money

@dataclass
class Order:
    id: str
    customer_id: str
    lines: list[OrderLine] = field(default_factory=list)
    MAX_ITEMS = 10

    def add(self, line: OrderLine) -> None:
        if self.item_count + line.quantity > self.MAX_ITEMS:
            raise OrderLimitExceeded(self.id)
        self.lines.append(line)

    @property
    def item_count(self) -> int:
        return sum(l.quantity for l in self.lines)

    def total(self) -> Money:
        return Money.sum(l.unit_price * l.quantity for l in self.lines)
```

```python
# ordering/ports/order_repository.py
from datetime import datetime
from typing import Protocol
from ordering.domain.order import Order

class OrderRepository(Protocol):
    def save(self, order: Order) -> None: ...
    def get(self, order_id: str) -> Order | None: ...

class Clock(Protocol):
    def now(self) -> datetime: ...
```

```python
# ordering/application/place_order.py
class PlaceOrder:
    def __init__(self, orders: OrderRepository, payments: PaymentGateway,
                 ids: IdGenerator, clock: Clock) -> None:
        self._orders, self._payments, self._ids, self._clock = orders, payments, ids, clock

    def __call__(self, cmd: PlaceOrderCommand) -> str:
        order = Order(id=self._ids.new(), customer_id=cmd.customer_id)
        for line in cmd.lines:
            order.add(line)
        self._payments.charge(cmd.customer_id, order.total())
        self._orders.save(order)
        return order.id
```

```python
# bootstrap/container.py  (the only place that knows concrete adapters)
def build_app(settings) -> App:
    orders = PostgresOrderRepository(settings.database_url)
    payments = StripePaymentGateway(settings.stripe_key)
    return App(place_order=PlaceOrder(orders, payments, UuidGenerator(), SystemClock()))
```

## Code shape (TypeScript)

```ts
// ordering/ports.ts
export interface OrderRepository {
  save(order: Order): Promise<void>;
  get(id: OrderId): Promise<Order | undefined>;
}

// ordering/application/placeOrder.ts
export class PlaceOrder {
  constructor(
    private readonly orders: OrderRepository,
    private readonly payments: PaymentGateway,
    private readonly clock: Clock,
  ) {}
  async execute(cmd: PlaceOrderCommand): Promise<OrderId> { /* domain logic via Order */ }
}

// bootstrap/main.ts
const placeOrder = new PlaceOrder(new PgOrderRepository(pool), new StripeGateway(key), systemClock);
app.post("/orders", httpPlaceOrder(placeOrder)); // inbound adapter translates HTTP <-> command
```

Other stacks: Java/Kotlin and C# use interfaces plus constructor injection (a container such as
Spring or Microsoft.Extensions.DependencyInjection is fine, but keep its annotations out of
`domain/`). Go: small consumer-side interfaces, wiring in `main.go` or `cmd/`. Rust: traits, with
generics or `Box<dyn Trait>`/`Arc<dyn Trait>` injected in `main`.

## Fakes

A fake is a working implementation kept deliberately simple. It lives in the test tree, not in
production code.

```python
# tests/ordering/fakes/in_memory_orders.py
class InMemoryOrderRepository:
    def __init__(self) -> None:
        self._rows: dict[str, Order] = {}
    def save(self, order: Order) -> None:
        self._rows[order.id] = copy.deepcopy(order)   # copy: mimic persistence, avoid aliasing
    def get(self, order_id: str) -> Order | None:
        o = self._rows.get(order_id)
        return copy.deepcopy(o) if o else None

class FakePaymentGateway:
    def __init__(self, decline_for: set[str] = frozenset()) -> None:
        self.charges: list[tuple[str, Money]] = []
        self._decline_for = decline_for
    def charge(self, customer_id: str, amount: Money) -> None:
        if customer_id in self._decline_for:
            raise PaymentDeclined(customer_id)
        self.charges.append((customer_id, amount))

class FixedClock:
    def __init__(self, at: datetime) -> None: self.at = at
    def now(self) -> datetime: return self.at
```

Rules for fakes:

- Behave like the real thing for everything the contract covers, including not-found, duplicates
  and ordering where the contract specifies them.
- Copy on save and load so tests cannot pass because of shared references.
- Expose inspection helpers (`charges`, `sent_emails`) for assertions on outcomes, and failure
  switches (`decline_for`) for error paths. Do not script call sequences.
- No fake for the domain itself. Domain objects are used for real in every test.

## Use case tests

```python
def test_order_over_limit_is_rejected_and_nothing_is_charged():
    orders, payments = InMemoryOrderRepository(), FakePaymentGateway()
    place = PlaceOrder(orders, payments, SequentialIds(), FixedClock(T0))

    with pytest.raises(OrderLimitExceeded):
        place(PlaceOrderCommand("c1", lines=[line(qty=11)]))

    assert payments.charges == []
    assert orders.get("order-1") is None
```

Assert on outcomes: what is stored, what was charged, what was sent, what was returned or raised.
Avoid `assert_called_once_with` on internal collaborators.

## Contract tests

One suite per driven port, parameterised over implementations. The fake runs everywhere; the real
adapter runs in the integration job.

```python
# tests/ordering/contracts/test_order_repository_contract.py
@pytest.fixture(params=["fake", pytest.param("postgres", marks=pytest.mark.integration)])
def repo(request, pg_url):
    if request.param == "fake":
        return InMemoryOrderRepository()
    return PostgresOrderRepository(pg_url)

def test_saved_order_round_trips(repo):
    order = make_order(lines=[line(qty=2)])
    repo.save(order)
    assert repo.get(order.id) == order

def test_missing_order_returns_none(repo):
    assert repo.get("nope") is None

def test_save_overwrites_existing(repo): ...
```

TypeScript: export a function `orderRepositoryContract(name, makeRepo)` that registers
`describe` blocks, and call it from both the fake's test file and the integration test file.

When a real adapter fails a contract test the fake passes, fix whichever one is wrong and add the
case. That is the point of the suite: the fake stays honest, so use case tests stay trustworthy.

## Enforcing the boundary

Add the check in the first slice and wire it into the normal test or lint command.

| Stack        | Tool                                              | Rule to express                               |
|--------------|---------------------------------------------------|-----------------------------------------------|
| Python       | import-linter (`layers` and `forbidden` contracts) | domain/application/ports must not import adapters, ORMs, web frameworks, SDKs |
| TS / JS      | dependency-cruiser or eslint-plugin-boundaries    | same, by path pattern                          |
| Java / Kotlin| ArchUnit                                          | classes in `..domain..` depend only on `..domain..` and the JDK |
| C# / .NET    | NetArchTest or ArchUnitNET                        | same                                           |
| Go           | depguard (golangci-lint) or go-arch-lint          | core packages may not import adapter or vendor packages |
| Rust         | separate crates: core crate has no infra deps in Cargo.toml | the compiler enforces it                 |

If adding a tool is not welcome, a small test that scans core source files for forbidden imports is
acceptable and better than nothing. Make its failure message name the offending file and the rule.

## Migration recipes

Work in thin vertical slices; keep the old path working until the new one is proven.

- **Extract the clock and IDs first.** Replace `now()` and random IDs in business logic with
  injected `Clock` and `IdGenerator` ports. Cheap, and it makes everything after it testable.
- **Wrap before you move.** Put an existing data-access module behind a port by writing a thin
  adapter that delegates to it. Point the logic at the port. Replace the internals later.
- **Peel ORM models off the domain.** If ORM models are the domain objects, introduce domain
  classes and mapping in the repository adapter, one aggregate at a time. If that is too costly now,
  record it as debt and still route access through a repository port.
- **Thin the controllers.** Move logic out of HTTP handlers, views or jobs into an application
  service; the handler becomes an inbound adapter that parses input, calls the use case and formats
  output.
- **Replace mocks with fakes as you touch tests.** For each port, write the fake and its contract
  suite once, then convert the tests in the slice you are working on. Do not rewrite the whole test
  suite in one go.
- **Characterise before changing.** Where tests are thin, write characterisation tests at the
  entry point (HTTP or CLI) that pin current behaviour, then refactor beneath them.
- **Anti-corruption layer for legacy or external models.** When a context must consume another
  system's model, translate it in an adapter so foreign concepts do not leak into the core.

## Smells to report

- Domain or application code importing a framework, ORM, HTTP client, SDK, env or filesystem.
- Ports named after technology, or ports that mirror a vendor's API instead of the use case's need.
- One giant repository or service interface used by many unrelated use cases.
- Business rules in controllers, serializers, ORM hooks, database triggers or front-end code only.
- Domain objects returned directly as API responses, or request DTOs passed into the domain.
- Tests that need a database or network to check a pure business rule.
- Heavy mocking of internal collaborators; assertions on call order rather than outcomes.
- `new ConcreteAdapter()` or service-locator lookups inside the core.
- One "Customer" (or similar) type stretched across several bounded contexts.
