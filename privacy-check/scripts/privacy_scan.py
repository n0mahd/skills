#!/usr/bin/env python3
"""Mechanical privacy and security checks for a git repo, run before merging to main or deploying.

Usage:
  privacy_scan.py [--repo DIR] [--base REF] [--url https://app.example] [--own-domain example.com ...] [--deps]

  --base REF   scan only lines changed since merge-base(REF, HEAD); default: scan every tracked file
  --url URL    also probe the live deployment for exposed files and missing headers
  --own-domain domains that count as first-party (repeatable); the --url host is added automatically
  --deps       run `npm audit` / `pip-audit` where a lockfile exists

Exit status: 1 if any FAIL, else 0. WARN and INFO lines are for the reviewer to judge.
Only the Python standard library is used; run with `python3 -I`.
"""
import argparse
import json
import os
import re
import shutil
import subprocess
import sys
import urllib.error
import urllib.parse
import urllib.request
import uuid

SKIP_DIRS = ("node_modules/", "vendor/", "dist/", "build/", ".next/", "test-results/", "worktrees/", "coverage/")
SKIP_FILES = re.compile(r"(package-lock\.json|yarn\.lock|pnpm-lock\.yaml|Cargo\.lock|poetry\.lock|\.min\.js|\.map)$")
TEXT_EXT = re.compile(r"\.(js|mjs|cjs|ts|tsx|jsx|py|rb|go|rs|java|kt|swift|php|html|htm|css|vue|svelte|json|ya?ml|toml|ini|cfg|conf|sh|bash|env|sql|md|txt|example|sample)$|(^|/)(Dockerfile|Makefile|\.env[^/]*)$")
CODE_EXT = re.compile(r"\.(js|mjs|cjs|ts|tsx|jsx|py|rb|go|rs|java|kt|swift|php|html|htm|vue|svelte|sh)$")
TEST_PATH = re.compile(r"(^|/)(tests?|__tests__|spec|e2e|fixtures?)/|\.(test|spec)\.")

SENSITIVE_FILE = re.compile(
    r"(^|/)(\.env(\.[^/]*)?|.*\.(db|sqlite3?|db-wal|db-shm|pem|key|p12|pfx|jks|keystore|mobileprovision)"
    r"|id_(rsa|ed25519|ecdsa)|credentials(\.json)?|service-account.*\.json|\.npmrc|\.pypirc|\.netrc|htpasswd)$",
    re.I,
)
SENSITIVE_FILE_OK = re.compile(r"\.(example|sample|template|dist)$|\.env\.(example|sample|template)$", re.I)

# High-confidence credential formats: a match is a FAIL.
SECRET_PATTERNS = [
    ("private key block", re.compile(r"-----BEGIN (RSA |EC |OPENSSH |DSA |PGP )?PRIVATE KEY")),
    ("AWS access key", re.compile(r"\bAKIA[0-9A-Z]{16}\b")),
    ("GitHub token", re.compile(r"\b(gh[pousr]_[A-Za-z0-9]{30,}|github_pat_[A-Za-z0-9_]{40,})\b")),
    ("Slack token", re.compile(r"\bxox[abprs]-[A-Za-z0-9-]{10,}")),
    ("Stripe live key", re.compile(r"\b[sr]k_live_[A-Za-z0-9]{16,}")),
    ("Anthropic/OpenAI key", re.compile(r"\bsk-(ant-)?[A-Za-z0-9_-]{32,}")),
    ("Resend key", re.compile(r"\bre_[A-Za-z0-9]{8,}_[A-Za-z0-9]{16,}")),
    ("Google API key", re.compile(r"\bAIza[0-9A-Za-z_-]{35}\b")),
    ("Telegram bot token", re.compile(r"\b\d{8,10}:AA[A-Za-z0-9_-]{33}\b")),
    ("credential in URL", re.compile(r"\b[a-z][a-z0-9+.-]*://[^/\s:@'\"]+:[^/\s:@'\"]{6,}@[^\s'\"]+", re.I)),
    ("signed JWT", re.compile(r"\beyJ[A-Za-z0-9_-]{10,}\.eyJ[A-Za-z0-9_-]{10,}\.[A-Za-z0-9_-]{10,}")),
]
# Hard-coded value assigned to a secret-looking name: a WARN (often a dev default or placeholder).
GENERIC_SECRET = re.compile(
    r"(secret|api[_-]?key|access[_-]?token|auth[_-]?token|password|passwd|private[_-]?key|client[_-]?secret)"
    r"[\"']?\s*[:=]\s*[\"']([^\"'\s]{10,})[\"']",
    re.I,
)
PLACEHOLDER = re.compile(r"change[-_]?me|example|placeholder|your[-_]|xxx|<|\$\{|process\.env|os\.environ|dummy|test|fake|redacted", re.I)

LOG_CALL = re.compile(r"\b(console\.(log|info|warn|error|debug)|logger\.\w+|log\.(info|warn|error|debug)|print\(|logging\.\w+|println!?|fmt\.Print|Sentry\.capture\w*|captureException|track\()")
PII_WORD = re.compile(r"email|e_mail|phone|password|passwd|token|otp|secret|cookie|authorization|req\.body|req\.headers|request\.(body|headers)|\bip\b|req\.ip|remoteAddress|address|birth|ssn|location|latitude|longitude|user(name)?\b|player_?name|full_?name", re.I)

URL_RE = re.compile(r"""(?:src|href|action|url\(|@import|fetch\(|axios\.\w+\(|new\s+WebSocket\(|io\()\s*=?\s*["'(]?\s*(https?:)?//([a-z0-9.-]+\.[a-z]{2,})""", re.I)
SERVER_OUTBOUND = re.compile(r"""\b(fetch|axios\.\w+|got|request|urlopen|requests\.\w+|httpx\.\w+|http\.(get|request)|https\.(get|request))\(\s*[`"']https?://([a-z0-9.-]+)""", re.I)
CLIENT_STORAGE = re.compile(r"\b(localStorage|sessionStorage|indexedDB|document\.cookie|AsyncStorage|SecureStore|UserDefaults|SharedPreferences)\b")
SCHEMA_CHANGE = re.compile(r"\b(CREATE\s+TABLE|ALTER\s+TABLE|ADD\s+COLUMN|addColumn|createTable|models\.\w+Field|Column\()", re.I)
ANALYTICS_SDK = re.compile(r"google-analytics|googletagmanager|gtag\(|segment\.(com|io)|mixpanel|amplitude|hotjar|fullstory|posthog|heap(analytics)?|clarity\.ms|facebook\.net|connect\.facebook|fbq\(|tiktok|sentry|bugsnag|datadog|logrocket|newrelic|intercom|plausible|umami|matomo", re.I)

PROBE_PATHS = [
    ".env", ".env.local", ".env.production", "backend/.env", "server/.env", "api/.env", ".git/config", ".git/HEAD",
    ".gitignore", "package.json", "package-lock.json", "backend/package.json", "node_modules/", "backend/",
    "server/", "api/", "scripts/", "documents/", "AGENTS.md", "CLAUDE.md", "README.md", "SETUP.md", "docker-compose.yml",
    "Dockerfile", "game.db", "backend/game.db", "db.sqlite", "database.sqlite", "data.db", "backup.sql", "dump.sql",
    "server.js", "backend/server.js", "config.js", "backend/config.js", ".DS_Store", ".vscode/settings.json",
    "wp-config.php", ".aws/credentials", "id_rsa",
]

results = []  # (level, check, message)


def add(level, check, message):
    results.append((level, check, message))


def git(repo, *args):
    return subprocess.run(["git", "-C", repo, *args], capture_output=True, text=True, check=False).stdout


def skip(path):
    return any(path.startswith(d) or f"/{d}" in path for d in SKIP_DIRS) or bool(SKIP_FILES.search(path))


def redact(s):
    s = s.strip()
    return s if len(s) <= 12 else f"{s[:4]}…{s[-2:]} ({len(s)} chars)"


def tracked_lines(repo):
    """Yield (path, lineno, line) for every tracked text file."""
    for path in git(repo, "ls-files").splitlines():
        if skip(path) or not TEXT_EXT.search(path):
            continue
        full = os.path.join(repo, path)
        try:
            if os.path.getsize(full) > 2_000_000:
                continue
            with open(full, encoding="utf-8", errors="replace") as fh:
                for n, line in enumerate(fh, 1):
                    yield path, n, line.rstrip("\n")
        except OSError:
            continue


def changed_lines(repo, base):
    """Yield (path, lineno, line) for lines added since merge-base(base, HEAD), including uncommitted edits."""
    mb = git(repo, "merge-base", base, "HEAD").strip()
    if not mb:
        sys.exit(f"cannot find merge-base of {base} and HEAD")
    diff = git(repo, "diff", "--unified=0", "--no-color", "--no-ext-diff", mb)
    path, n = None, 0
    for line in diff.splitlines():
        if line.startswith("+++ "):
            path = line[6:] if line.startswith("+++ b/") else None
        elif line.startswith("@@"):
            m = re.search(r"\+(\d+)", line)
            n = int(m.group(1)) if m else 0
        elif line.startswith("+") and path and not skip(path):
            yield path, n, line[1:]
            n += 1
    return mb


def check_tracked_files(repo):
    bad = [p for p in git(repo, "ls-files").splitlines() if SENSITIVE_FILE.search(p) and not SENSITIVE_FILE_OK.search(p)]
    for p in bad:
        add("FAIL", "tracked-secret-file", f"{p} is tracked by git; remove it, rotate anything in it, and gitignore it")
    ignored = git(repo, "check-ignore", "--no-index", ".env", "backend/.env", "x.db", "x.sqlite").split()
    if ".env" not in ignored:
        add("WARN", "gitignore", ".env is not gitignored")


def check_lines(lines, mode):
    seen_hosts, storage, schema, logs = {}, [], [], []
    for path, n, line in lines:
        loc = f"{path}:{n}"
        is_test = bool(TEST_PATH.search(path))
        for name, rx in SECRET_PATTERNS:
            m = rx.search(line)
            if m and not (name == "signed JWT" and is_test) and not PLACEHOLDER.search(m.group(0)):
                add("FAIL", "secret", f"{loc} {name}: {redact(m.group(0))}")
        m = GENERIC_SECRET.search(line)
        if m and not PLACEHOLDER.search(m.group(2)) and not is_test:
            add("WARN", "hardcoded-secret", f"{loc} `{m.group(1)}` assigned literal {redact(m.group(2))}")
        if not CODE_EXT.search(path):
            continue
        if not is_test and LOG_CALL.search(line) and PII_WORD.search(line):
            logs.append(f"{loc} {line.strip()[:140]}")
        if ANALYTICS_SDK.search(line) and not is_test:
            add("WARN", "third-party-tracker", f"{loc} analytics/error SDK reference: {line.strip()[:120]}")
        for m in URL_RE.finditer(line):
            seen_hosts.setdefault(m.group(2).lower(), loc)
        for m in SERVER_OUTBOUND.finditer(line):
            seen_hosts.setdefault(m.group(m.lastindex).lower(), loc)
        if CLIENT_STORAGE.search(line) and not is_test:
            storage.append(f"{loc} {line.strip()[:120]}")
        if SCHEMA_CHANGE.search(line):
            schema.append(f"{loc} {line.strip()[:120]}")
    for entry in logs:
        add("WARN", "log-pii", f"log call near personal/secret data: {entry}")
    for host, loc in sorted(seen_hosts.items()):
        add("INFO", "third-party-origin", f"{host} (first seen {loc})")
    if mode == "diff":
        for entry in storage:
            add("WARN", "client-storage", f"new client-side storage: {entry}")
        for entry in schema:
            add("WARN", "schema-change", f"data model changed, update the data inventory: {entry}")
    else:
        if storage:
            add("INFO", "client-storage", f"{len(storage)} client-side storage uses (inventory them): " + "; ".join(s.split(' ', 1)[0] for s in storage[:12]))
        if schema:
            add("INFO", "schema", f"{len(schema)} schema statements (inventory every personal field): " + "; ".join(s.split(' ', 1)[0] for s in schema[:12]))
    return seen_hosts


def filter_first_party(own_domains):
    own = [d.lower().lstrip(".") for d in own_domains]
    kept = []
    for level, check, msg in results:
        if check == "third-party-origin":
            host = msg.split(" ", 1)[0]
            if host in ("localhost", "127.0.0.1", "example.com", "www.w3.org") or any(host == d or host.endswith("." + d) for d in own):
                continue
        kept.append((level, check, msg))
    results[:] = kept


def fetch(url, timeout=10):
    req = urllib.request.Request(url, headers={"User-Agent": "privacy-check/1"})
    try:
        with urllib.request.urlopen(req, timeout=timeout) as r:
            return r.status, dict((k.lower(), v) for k, v in r.headers.items()), r.read(4096)
    except urllib.error.HTTPError as e:
        return e.code, dict((k.lower(), v) for k, v in e.headers.items()), b""
    except Exception as e:  # noqa: BLE001
        return None, {}, str(e).encode()


def check_live(repo, url):
    base = url.rstrip("/") + "/"
    status, headers, body = fetch(base)
    if status is None:
        add("FAIL", "live", f"{base} unreachable: {body.decode(errors='replace')}")
        return
    _, _, fallback = fetch(base + f"no-such-path-{uuid.uuid4().hex}")
    paths = list(PROBE_PATHS)
    # Also probe every tracked server-side file: if nginx serves the checkout, these leak.
    for p in git(repo, "ls-files").splitlines():
        if re.match(r"(backend|server|api|scripts|supabase|migrations|config|cli|mcp)/", p) or re.search(r"\.(sh|sql|env\.example|md)$", p):
            if not skip(p) and p not in paths:
                paths.append(p)
    exposed, cached = [], set()
    for p in paths[:150]:
        for _ in range(2):  # CDNs answer from different edges; one clean reply proves nothing
            s, h, b = fetch(base + urllib.parse.quote(p))
            if s == 200 and b and b != fallback and b != body:
                exposed.append(p)
                if h.get("cf-cache-status") == "HIT" or h.get("x-cache", "").upper().startswith("HIT") or "age" in h:
                    cached.add(p)
                break
    sensitive = [p for p in exposed if SENSITIVE_FILE.search(p.rstrip("/")) or p.startswith(".git") or p.rstrip("/") in ("backend", "server", "api", "node_modules")]
    note = lambda p: " (from CDN cache: fix the origin, then purge this URL)" if p in cached else ""
    for p in sensitive:
        add("FAIL", "live-exposure", f"{base}{p} is publicly served{note(p)}")
    for p in exposed:
        if p not in sensitive:
            add("WARN", "live-exposure", f"{base}{p} is publicly served (source/docs: is that intended?){note(p)}")
    if not base.startswith("https://"):
        add("FAIL", "live-headers", "deployment is not HTTPS")
    wanted = {
        "strict-transport-security": "HSTS",
        "content-security-policy": "CSP (limits what an XSS can steal, e.g. tokens in localStorage)",
        "x-content-type-options": "X-Content-Type-Options: nosniff",
        "referrer-policy": "Referrer-Policy (stops URLs with room codes/tokens leaking to other sites)",
    }
    for h, why in wanted.items():
        if h not in headers:
            add("WARN", "live-headers", f"missing {why}")
    if "x-frame-options" not in headers and "frame-ancestors" not in headers.get("content-security-policy", ""):
        add("WARN", "live-headers", "missing clickjacking protection (X-Frame-Options or CSP frame-ancestors)")
    for h in ("x-powered-by", "server"):
        if re.search(r"\d", headers.get(h, "")):
            add("INFO", "live-headers", f"{h} reveals a version: {headers[h]}")
    for cookie in [v for k, v in headers.items() if k == "set-cookie"]:
        if "secure" not in cookie.lower() or "httponly" not in cookie.lower():
            add("WARN", "live-cookies", f"cookie without Secure/HttpOnly: {cookie.split(';')[0].split('=')[0]}")


def check_deps(repo):
    for lock in git(repo, "ls-files", "*package-lock.json").splitlines():
        if skip(lock) or not shutil.which("npm"):
            continue
        d = os.path.join(repo, os.path.dirname(lock))
        out = subprocess.run(["npm", "audit", "--omit=dev", "--json"], cwd=d, capture_output=True, text=True, timeout=120).stdout
        try:
            vulns = json.loads(out).get("metadata", {}).get("vulnerabilities", {})
        except json.JSONDecodeError:
            add("WARN", "deps", f"npm audit failed in {lock}")
            continue
        high = vulns.get("high", 0) + vulns.get("critical", 0)
        if high:
            add("FAIL", "deps", f"{lock}: {vulns.get('critical', 0)} critical, {vulns.get('high', 0)} high production vulnerabilities (npm audit)")
        elif vulns.get("moderate", 0):
            add("WARN", "deps", f"{lock}: {vulns['moderate']} moderate production vulnerabilities")
    reqs = [p for p in git(repo, "ls-files", "*requirements*.txt", "*pyproject.toml").splitlines() if not skip(p)]
    if reqs and shutil.which("pip-audit"):
        for r in reqs:
            if r.endswith(".txt"):
                p = subprocess.run(["pip-audit", "-r", os.path.join(repo, r)], capture_output=True, text=True, timeout=180)
                if p.returncode:
                    add("FAIL", "deps", f"{r}: pip-audit reports vulnerabilities")


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--repo", default=".")
    ap.add_argument("--base")
    ap.add_argument("--url")
    ap.add_argument("--own-domain", action="append", default=[])
    ap.add_argument("--deps", action="store_true")
    a = ap.parse_args()
    repo = os.path.abspath(a.repo)
    head = git(repo, "rev-parse", "--short", "HEAD").strip()
    if not head:
        sys.exit(f"{repo} is not a git repo with commits")

    check_tracked_files(repo)
    if a.base:
        check_lines(changed_lines(repo, a.base), "diff")
        scope = f"lines changed since merge-base with {a.base}"
    else:
        check_lines(tracked_lines(repo), "full")
        scope = "all tracked files"
    own = list(a.own_domain)
    if a.url:
        own.append(urllib.parse.urlparse(a.url).hostname or "")
        check_live(repo, a.url)
    filter_first_party(own)
    if a.deps:
        check_deps(repo)

    print(f"privacy-scan {repo} @ {head} ({scope})")
    order = {"FAIL": 0, "WARN": 1, "INFO": 2}
    for level, check, msg in sorted(results, key=lambda r: (order[r[0]], r[1])):
        print(f"{level:4} [{check}] {msg}")
    counts = {k: sum(1 for r in results if r[0] == k) for k in order}
    print(f"\n{counts['FAIL']} FAIL, {counts['WARN']} WARN, {counts['INFO']} INFO")
    return 1 if counts["FAIL"] else 0


if __name__ == "__main__":
    sys.exit(main())
