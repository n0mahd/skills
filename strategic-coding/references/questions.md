# Strategic coding: questions, examples and the note

## Question bank

Use the questions that earn their keep; skip the rest.

### Place the work

- What is the user trying to achieve, and would they call this done if only the literal request
  were met?
- Which module owns the concept involved? Is the place the request surfaced that module?
- Which invariants or priorities on the strategy page touch this area? Are any enforced only by
  convention?
- What does the blast-radius table say about this area? If there is none: who imports or calls
  this, what reads the data it writes, what runs it on a schedule?
- What does history say? A previous attempt, a revert, an earlier fix of the same thing, a comment
  or ADR explaining the odd part?

### Need, cause and related code

- For a fix: what is the smallest check that fails today? Why was this possible, and why was
  *that* possible? (Stop when the answer leaves the code.)
- For a feature: what problem does it solve? Does something already solve most of it? Does the
  requested shape fight an invariant or the direction?
- Where else does the same concept, call, idiom, copied block or assumption appear?
- Would a new contributor make this mistake, or have to repeat this work, tomorrow? What would
  stop them?

### Level and fit

- What are the local, home, class and design options here, concretely?
- Which option meets the need at its home with the smallest blast radius?
- Does the change use the existing home for this concept, or add a second way?
- Does it move with the stated direction or against it?
- Will the next change in this direction be easier or harder afterwards?
- Which callers see different behaviour afterwards, and is that intended?
- How would we roll it back? Is there stored data, a migration or a cache that makes that hard?

### Leave it better

- Do the tests pin behaviour the user relies on? Does a regression test fail on the old code?
- What is the cheapest guard against any class of mistake found: type, assertion, lint rule,
  contract test?
- Which doc became wrong because of this change?
- What did I learn that only lives in this conversation?

## Worked examples

### A new feature that overlaps an existing one

Request: add CSV export to the orders page.

- Local: a new export button and a CSV writer in the orders page. Quick, but the reports page
  already exports PDF through a `ReportExporter` with its own column formatting and permissions.
- At the home: add CSV as a format to `ReportExporter`, and give the orders page the same export
  entry point. Permissions and column formatting come for free and stay consistent.
- For the class: none needed yet; one exporter with two formats is fine.
- Fit: the strategy page says "server-side generation for anything users download", so the CSV is
  built on the server, not in the browser.
- Chosen: at the home. Noted for the owner: the reports page's PDF and the new CSV now share
  column definitions, so a column rename changes both.

### A crash on a missing field

Report: the invoice page crashes when `customer.address` is null.

- Local: `customer.address?.line1 ?? ""` in the template. Hides the crash; the PDF export and the
  email have the same bug.
- Cause: the API sometimes returns customers without addresses (legacy imports), but the
  `Customer` type says `address: Address`. The type lies.
- For the class: fix the type to `address: Address | null`, let the compiler list every unsafe use
  (four sites), and handle each. Add a fixture with a null address to the shared test data.
- Chosen: class, because the type fix is cheap and the compiler finds the related sites. Owner
  decision raised: backfill legacy addresses or keep them optional?

### A flaky test

Report: `checkout.test` fails one run in ten.

- Local: add a retry or a sleep. Hides it; the race is real in production too.
- Cause: the order total is computed from a cache that is warmed asynchronously.
- Related: three other services read the same cache without awaiting the warm-up.
- Chosen: fix it at the home in the cache module (expose a `ready` promise, await it where the
  service is created), fix the three related sites since they are the same mechanical change, and
  seed the test clock. Recorded in the debt register: the cache has no documented owner.

### A config change

Request: raise the upload limit from 10 MB to 50 MB.

- The limit appears in the web server config, the API validator and a frontend constant, all
  hardcoded. Changing one leaves the others rejecting uploads.
- At the home (such as it is): change all three in one change, and note the duplication.
- For the class (proposed, not taken, outside scope): one config value served to the frontend and
  read by both the server and the validator.
- Fit: the strategy page lists "one config reader" as direction, so the proposal goes in the debt
  register with the three paths.

### When the right answer is local

Production is down because a vendor returns a new enum value. Patch locally first (map unknown
values to a safe default and log them), labelled as a stopgap, deployed now. Then the real fix (a
tolerant parser at the adapter boundary and a contract test against the vendor's schema) as a
follow-up, recorded with an owner and a date.

## Strategic note template

```
Strategic note (standard)
- Need / root cause: <one sentence>. ("Why" chain stopped at: <level>.)
- Level: <local | home | class | design>, because <reason>. Considered: <higher option, why not>.
- Related code: changed <paths>; left <paths> (recommend <action>).
- Fit: <direction / invariant / blast radius>. Docs updated: <paths or none>.
- Tests and guards: <test or rule>, proven by <how>.
- Owner decisions: <question> (recommend <answer>).
```
