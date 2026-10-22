---
name: privacy-check
description: Privacy and security gate for apps that hold user data, run before every merge to main and every deploy. Scans for leaked secrets, exposed files, personal data in logs and new third parties, probes the live site, reviews the change against a checklist and keeps the repo's data inventory (documents/privacy.md) true. Also use when adding analytics, usage metrics, error reporting, logging, a new personal-data field or a third-party service, or when the user asks "are we good privacy-wise".
---

# Privacy check

Prove three things before code reaches `main` or production:

1. **We collect what the inventory says, and nothing more.** A new personal field, log line,
   storage key or third party is a decision someone made on purpose, not a side effect.
2. **What we hold can't leak through an ordinary mistake.** No served `.env`, no committed
   database, no token in a log, no XSS that can read the session.
3. **We learn about usage and errors without identifying anyone.** Count events, don't follow people.

The user's stance: protect people's data, never track individuals, understand usage only in
aggregate, find bugs without needing to know who hit them, anonymize wherever possible.
Collection is already minimal, so the job is to keep it minimal and stop leaks.

## Modes

- **Gate (default)**: before a merge to `main` or a deploy. Scope is the diff since
  `merge-base(origin/main, HEAD)` (or since the last deployed commit), plus the live probe.
- **Baseline**: the first run on a repo, after an incident, or when asked for a full audit.
  Scope is the whole repo and the live site; it produces or rewrites `documents/privacy.md`.

## Procedure

1. **Orient.** Read the repo's `AGENTS.md` (production URL, deploy path, what must not be
   touched) and `documents/privacy.md`. If the inventory is missing, switch to baseline mode
   and create it from [templates/privacy.md](templates/privacy.md). Check whether the repo is
   public (`gh repo view --json visibility`), and read the private findings register
   `~/Knowledge/memory/<project>-privacy-findings.md` if it exists.
2. **Run the scanner** from the repo root. It uses only the standard library:

   ```bash
   python3 -I ~/Skills/privacy-check/scripts/privacy_scan.py --repo . \
     --base origin/main --url https://<prod-host> --own-domain <first-party-domain> --deps
   ```

   Drop `--base` in baseline mode. Any `FAIL` blocks the merge or deploy. `WARN` lines need a
   decision from you: fix it, record it in the inventory, or explain why it's fine. The scanner
   matches strings, not data flows, so a clean run proves very little.
3. **Review by hand** against [references/checklist.md](references/checklist.md). In gate
   mode, cover each checklist section the diff touches, and always cover the "every time"
   section. Trace personal data from where it enters, through storage and logs, to every place
   it leaves. Read the code paths. Don't trust function names: an `escapeHtml` that skips quotes
   is still an XSS.
4. **Check telemetry.** If the change adds or alters analytics, metrics, logging or error
   reporting, hold it to [references/telemetry.md](references/telemetry.md). Identifying
   telemetry blocks the change, even when it's "only for debugging".
5. **Reconcile the inventory.** `documents/privacy.md` must describe the code after the merge:
   personal data fields, logs, client storage, third parties, retention, open findings. Update
   it in the same change. A stale inventory is a failed check.
6. **Turn promises into tests where it's cheap.** If the inventory says "logs never contain
   email", add a test that drives the route and asserts that. See [[privacy-guarantees-not-promises]].
7. **After a deploy**, run the scanner again with `--url` and confirm what users get: the fix is
   live, nothing new is exposed, and the CDN isn't serving a stale copy. Edge caches keep files
   from before a lockdown, so after fixing an exposure at the origin, purge those URLs.
8. **Report** (format below). Record every finding you didn't fix in the private register
   `~/Knowledge/memory/<project>-privacy-findings.md` (add it to `memory/index.md`), so the next
   run sees them. Delete a row when its fix ships.

## Verdict

- **Block**: any scanner `FAIL`, or a High finding. High means: a secret or personal data
  reachable by outsiders; an auth bypass or IDOR on personal data; an injection or XSS that
  reaches tokens or personal data; personal data sent to a third party missing from the
  inventory; telemetry that identifies a person or device; or a leaked credential still not
  rotated.
- **Ship with follow-ups**: only medium or low findings, each recorded in the private register
  with a concrete fix.
- **Ship**: nothing found. Say what you checked and what you couldn't check.

Report in this order: the verdict in one line, then findings ranked most severe first. Give each
finding as `file:line` (or URL), what an attacker or a careless log could do with it, and the
smallest fix. Then the inventory changes you made, then any blind spots (for example "couldn't
read the production nginx config").

## Rules

- **Unfixed findings never go into the repo, its issues, PRs or commit messages** when the repo
  is public, and preferably not even when it's private. A pushed list of open holes is an
  exploit guide, and pushes can't be recalled: forks, caches and the commit SHA all outlive a
  deleted branch. Open findings and secret rotation status go in the private register only.
  The repo's `documents/privacy.md` describes what the app holds, not what's broken. A
  security-fix commit says what it changes, not how to exploit the old code, until it's
  deployed. Before pushing anything this skill wrote, re-read it with that in mind.
- Never print a secret's value. Name the file, the line and the kind of credential, and redact
  the rest. If a real credential was ever committed or served, it must be rotated: deleting the
  file doesn't un-leak it.
- Probe only the user's own deployments, with GET requests and no auth attacks, fuzzing or load.
- Fix findings inside the change you're gating. Record findings elsewhere in the codebase
  instead of widening the change, unless the user asks you to fix them.
- Changes to production (purging a CDN, editing nginx, rotating secrets, restarting services)
  follow the repo's deploy rules and need the user's go-ahead.
- "No evidence of X" is the strongest honest claim. Never call an app "secure".
