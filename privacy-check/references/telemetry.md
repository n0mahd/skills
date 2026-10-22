# Anonymous usage and error telemetry

Goal: answer "is the app used, what breaks, what's slow?" without being able to answer "what did
*this person* do?". If a dataset could reconstruct one person's session, it's tracking, whatever
it's called.

## Hard rules (any break blocks the change)

1. **No identifiers in telemetry.** No user ID, account ID, email, device ID, IP address,
   fingerprint, advertising ID, session ID or persistent client ID, and no hash of any of
   these: a stable hash is still an identifier.
2. **No third-party analytics or error SDKs** (Google Analytics, Segment, Mixpanel, PostHog
   cloud, Sentry SaaS, Hotjar and the like). Telemetry goes to our own endpoint and our own
   storage. A self-hosted tool is acceptable only when it is configured to follow these rules.
3. **No free text and no content.** Never record what users typed (names, messages, search
   terms), URLs with query strings or IDs, or page titles. Record route *templates*
   (`/rooms/:id`), enums and numbers.
4. **No raw IPs at rest.** Rate limiters may hold IPs in memory for their window. Access logs drop
   or truncate them (IPv4 /24, IPv6 /48) before they're written, or are kept for 7 days at most
   and say so in the inventory.
5. **Errors are scrubbed before they leave the process.** Keep the error class, message
   *template*, stack frames (file:line), release version, route template and a coarse
   environment (browser family and major version, OS family). Strip anything that came from the
   request: bodies, headers, cookies, query strings and values interpolated into messages.
6. **Everything has a retention limit.** Raw events last 30 days at most, and daily aggregates
   last as long as they're useful. The cleanup is code, not an intention.

## Patterns that answer real questions

- **Aggregate counters, not event streams.** Store `(day, event, dimension, count)` rows, such as
  `(2026-10-20, game_started, players=4, 17)`, and increment them on the server where the action
  already happens. That answers adoption, funnels ("rooms created → games started → games
  finished") and feature use without any per-user rows.
- **Coarse time.** Bucket by day, or by hour if that's needed. Precise timestamps plus a few
  dimensions single people out.
- **Small-count suppression.** When showing or exporting aggregates, merge or hide buckets with
  fewer than k (say 5) counts, so a rare combination can't point to one person.
- **Unique counts without IDs**, only if they're truly needed ("how many distinct players
  today?"): HMAC the user ID with a random salt that lives only in memory and rotates daily.
  Count distinct hashes for that day, store just the number, then discard the salt and the hashes.
  Nothing links today to tomorrow. Prefer not needing this at all.
- **Performance**: record histograms (latency buckets per route template), not per-request rows.
- **Client errors**: `window.onerror` / `unhandledrejection` → scrub (rule 5) → `navigator.sendBeacon('/api/telemetry/error', …)`
  to our endpoint, de-duplicated by a hash of `(message template, top frame, release)`. Store a
  count per fingerprint per day plus one sample stack trace. That's enough to find and fix the
  bug.
- **Server errors**: the same fingerprint-and-count approach in the error handler. The log line
  carries the fingerprint and the route template, never the request.
- **Debugging a specific user's problem**: the user sends a report on purpose, such as a "send
  diagnostics" button that shows them exactly what it will send. No silent per-user capture.

## Checks for a telemetry change

- Read the event schema: list every field and confirm each one is an enum, a number, a coarse
  time or a route template.
- Look for identifiers by data flow, not just by name: an `actorUserId` in an "audit" log line is
  per-user tracking unless it's justified as security audit data with a short retention.
- Confirm retention is enforced: a job, TTL or rotation exists and runs.
- Confirm consent isn't needed *because* nothing is personal. If the design needs a consent
  banner, it isn't anonymous: redesign it.
- Add or extend a test that triggers the event or error with realistic personal data in the
  request (an email, a name with quotes) and asserts none of it appears in the stored telemetry.
- Record the telemetry in `documents/privacy.md`: what is counted, where it's stored and how long
  it's kept.
