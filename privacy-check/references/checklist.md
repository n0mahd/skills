# Privacy and security checklist

Each item is phrased as the mistake to look for. "Every time" applies to every gate run. The
other sections apply whenever the diff touches that area, and all of them apply in baseline mode.

## Every time

- **Secrets**: no credential in the diff, the commit messages or test fixtures. `.env`,
  databases, keys and backups are gitignored *and* untracked (`git ls-files`). A secret that was
  ever committed or served is rotated, not just deleted.
- **Served files**: the web server serves an allow-list (built assets, `*.html`, a public dir),
  not the checkout root. A new top-level file or directory isn't reachable from the internet
  unless it's meant to be. Confirm against the live site, not the config's intent.
- **Inventory drift**: every new field, table, column, log line, cookie or storage key, outbound
  host and third-party script holding personal data appears in `documents/privacy.md`.
- **Logs and errors**: nothing logs request bodies, headers, tokens, OTPs, passwords, emails,
  phone numbers, IPs, precise locations or free text typed by users. Check `err` objects
  too: a provider's error response often echoes the recipient address or the API key. Error
  messages returned to clients don't carry stack traces, SQL or internal paths.
- **New third parties**: any new SDK, CDN script, font, iframe, email/SMS provider or API.
  What does it receive? Is it in the inventory? Could you self-host it or drop it?

## Authentication and sessions

- Login codes and one-time tokens: random from a CSPRNG, short-lived, single-use, stored
  hashed. Wrong guesses are capped per code, not only per IP (an attacker can rotate IPs).
- Session tokens: signed with a strong secret, which is rotated after any leak. Reasonable
  expiry in production. Revocable if the app needs that. Not placed in URLs, where they leak
  through history, logs and the Referer header.
- Tokens in `localStorage` can be read by any XSS on the origin. If they stay there, XSS
  hygiene and a CSP are the real defence; otherwise use `HttpOnly; Secure; SameSite` cookies.
- Account enumeration: "send me a code" and "forgot" flows give the same answer whether or not
  the account exists, and they're rate limited.
- Production config guards are actually on (for example `NODE_ENV=production`). Dev defaults
  (long expiry, CORS `*`, binding `0.0.0.0`, verbose errors) don't reach production.

## Authorization

- Every route and socket event that returns or changes personal data checks that the caller
  owns it or is in the same room, team or account, on the server. Look for IDOR: swap the ID in
  the URL and see whether the request still works.
- Lists and broadcasts don't include other people's emails or internal IDs unless the feature
  needs them. Check what Socket.IO, SSE or WebSocket payloads actually carry.
- Admin, debug, repair and MCP or agent endpoints are off or authenticated in production.

## Injection and output encoding

- SQL is parameterised everywhere. No string-built queries from user input.
- Every user-controlled string (names, room names, chat, filenames) is escaped for its context:
  HTML text, **attribute values (quotes included)**, URLs and JS. Check the escape helper
  itself, and check `innerHTML`, `dangerouslySetInnerHTML`, `v-html` and template literals
  assigned to the DOM.
- Outbound email and SMS escape user-controlled text in HTML bodies. They can't be turned into a
  relay: no arbitrary recipient plus arbitrary content from an unauthenticated or freely created
  account, and they're rate limited per sender and per recipient.
- Server-side fetches of user-supplied URLs are blocked or allow-listed (SSRF).

## Transport and headers

- HTTPS only, with HSTS. A CSP that disallows inline script, or at least restricts script
  sources and `connect-src`. `X-Content-Type-Options: nosniff`, a `Referrer-Policy` such as
  `strict-origin-when-cross-origin` or `no-referrer`, and `frame-ancestors` or `X-Frame-Options`.
- CORS is restricted to your own origins when cookies or credentials are involved.
- The CDN or proxy doesn't cache authenticated API responses, and it isn't serving stale copies
  of files that are now blocked.

## Data lifecycle

- Retention: every table, log and backup that holds personal data has a stated lifetime, and
  something enforces it (a cleanup job, TTL or log rotation). Used OTPs, expired codes and old
  sessions get deleted, not kept forever.
- Deletion: a user can delete their account and personal data. The inventory says what remains
  (for example anonymised game history) and why.
- Backups: encrypted or at least access-restricted, not in the web root, with retention.
- Journals and log files on the host: who can read them, and how long they're kept
  (`journalctl --disk-usage`, logrotate).
- Dev and test data never contain real users' personal data. Tests use dedicated test accounts.

## Client side

- `localStorage`, `sessionStorage`, IndexedDB and cookies: every key is in the inventory with
  its lifetime. Sign-out clears what it should, and a shared device doesn't keep someone else's
  session.
- No third-party scripts on pages that show personal data or handle login. Self-host fonts and
  libraries; use Subresource Integrity if a CDN is unavoidable.
- Native apps: secure storage for tokens, no personal data in crash or analytics SDKs, and
  privacy manifest or App Store nutrition labels that match the inventory.

## Dependencies and supply chain

- `npm audit --omit=dev` and `pip-audit` show no high or critical issues in production
  dependencies, or each one is assessed as unreachable.
- New dependencies are maintained, widely used and do what their name says. Install scripts are
  reviewed for anything new and obscure.
- Lockfiles are committed, and production installs with `npm ci` or the equivalent.
