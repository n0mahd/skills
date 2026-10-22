# Security audit playbook

Use the portions relevant to the target. The objective is a defensible install decision, not a ritual checklist.

## 1. Resolve the install target

Identify:

- the canonical upstream and whether redirects, mirrors, forks, or renamed projects are involved;
- the latest stable release and its tag/commit;
- the user's OS, architecture, package manager, and intended install method when known;
- whether the package recipe builds from source or installs a publisher-built artifact;
- submodules, Git LFS objects, vendored code, generated code, and downloaded build inputs.

Prefer authoritative release APIs, repository metadata, signed package indexes, and upstream documentation. Pin the audit to immutable identifiers. If the user supplied a repository URL without naming an install method, inspect both the latest release and the default branch, then state which one the verdict covers.

Clone public repositories into a fresh temporary directory. Read applicable repository instructions before examining or changing anything. Do not reuse an existing user checkout unless that checkout itself is the requested target.

## 2. Establish structure and attack surface

Inventory manifests, lockfiles, install scripts, build scripts, release workflows, executable files, large files, binary blobs, generated assets, and submodules. Useful static checks include:

```text
rg --files
git ls-tree -r -l <commit>
git submodule status
file <artifact>
readelf -d/-n/-Ws <ELF>
objdump -p <PE>
codesign and pkgutil inspection on macOS
```

Avoid `ldd` and similar mechanisms on an untrusted executable when a format parser can provide the same information without invoking its loader.

Look for obfuscation, packed or encrypted payloads, unexpected executable assets, high-entropy embedded data, runtime code download, dynamic loading, native extensions, and generated source whose generator or input is missing.

## 3. Trace behavior and sensitive data

Search broadly, then read complete functions and their callers. Keyword hits are leads, not findings.

### Outbound traffic

Find literal and constructed URLs, DNS names, sockets, HTTP clients, WebSockets, raw TCP/UDP, IPC, browser-opening calls, and endpoints received from remote responses. For each endpoint record:

- owner and purpose;
- trigger and default state;
- data, identifiers, headers, and query parameters sent;
- whether redirects and destination hosts are constrained;
- whether TLS verification can be disabled;
- whether response-provided URLs can reach arbitrary or local addresses.

### Sensitive sources

Check access to credentials, keyrings, cookies, browser profiles, SSH keys, cloud credentials, environment variables, home-directory scans, clipboard, microphone, camera, screen capture, location, contacts, messages, input events, device identifiers, hostname, username, machine ID, process list, and system logs.

Trace each sensitive source to local storage, logs, child processes, and network sinks. Inspect error and verbose logging separately; local leakage still matters even when nothing is uploaded.

### Execution and persistence

Inspect process spawning, shells, PowerShell, `eval`, reflection, dynamic imports, native FFI, unsafe code near trust boundaries, privilege escalation, sudo/polkit requests, registry changes, launch agents, scheduled tasks, systemd units, autostart entries, browser native-messaging hosts, services, and tray/background behavior.

Separate ordinary desktop integration from persistence that starts without a clear user choice.

### Filesystem and destructive behavior

Review recursive deletion, path construction, archive extraction, symlink handling, permission changes, migration code, self-update replacement, backup/rollback behavior, and writes outside application-specific directories. Check for zip-slip/path traversal and unsafe temporary files.

## 4. Audit installation, build, and updater paths

Read every script that can run during installation, removal, upgrade, build, or first launch:

- package lifecycle hooks and post-install scripts;
- Dockerfiles and CI/release workflows;
- `build.rs`, `setup.py`, PEP 517 backends, npm scripts, Makefiles, CMake, Gradle plugins, and code generators;
- `curl | sh`, remote scripts, unpinned downloads, and commands run as root;
- desktop hooks, services, kernel modules, udev rules, browser policies, and shell-profile edits.

For self-updaters, verify allowed hosts, redirect policy, size limits, archive extraction, signature or checksum validation, rollback, and when the downloaded payload is first executed. A checksum from the same release account protects transit integrity but not against account or CI compromise. Prefer signed metadata or reproducible builds.

## 5. Audit dependencies and feature resolution

Use the lockfile, not only manifest ranges. Record registry versus Git/path sources, exact Git revisions, checksums, patches, overrides, optional features, and lifecycle/build scripts.

Pay extra attention to:

- direct dependencies with broad system or network access;
- unusual, new, abandoned, typosquat-like, or single-maintainer packages;
- Git dependencies and forks;
- packages that execute during build or installation;
- optional analytics, crash reporting, metrics, WAM, tracing exporters, ad SDKs, or auto-update features;
- native prebuilt libraries and downloaded toolchains.

Confirm the resolved feature graph. The presence of telemetry code in a dependency repository is not a finding if the relevant crate/module and feature are absent from the target build.

Use an existing advisory scanner when possible. If tooling must be downloaded, isolate it from the target and say what was used. Examples include `cargo audit`, `npm audit --package-lock-only`, `pnpm audit`, `pip-audit`, `govulncheck`, `osv-scanner`, `bundler-audit`, and platform package advisories. Preserve the exact scan date and database freshness. Explain exploitability rather than reporting identifiers without context.

Do not imply that all transitive dependency source was manually reviewed when it was not. State the number scanned and which dependencies received deeper inspection.

## 6. Verify the release artifact without executing it

When an artifact is the likely install target:

1. Download it to the temporary audit directory from the authoritative release location.
2. Verify published hashes and signatures, noting whether they share the same trust root.
3. List archive contents before extraction and reject surprising absolute paths, traversal, device files, setuid files, or unexpected hooks.
4. Inspect executable format, imports, sections, signing/notarization metadata, embedded endpoints, and bundled configuration statically.
5. Compare contents with packaging declarations and release workflows.
6. Check whether tags and commits are signed and whether CI actions and build inputs are pinned immutably.
7. Look for reproducible-build attestations or provenance. If absent, state that the binary-to-source correspondence is unproven.

Do not run `--version` merely as a provenance check; a malicious program can execute before printing its version. Dynamic execution belongs in the optional sandboxed stage.

## 7. Optional dynamic analysis

Use dynamic analysis only when it adds material evidence and can be contained. Prefer a disposable VM or container with:

- no user home, secrets, account sessions, device access, or shared clipboard;
- a read-only target where possible;
- a fresh temporary writable area;
- network disabled first, then an instrumented allowlisted network if network behavior must be observed;
- syscall, file, process, DNS, and connection tracing;
- snapshots for rollback.

Some GUI, kernel, browser-extension, and account-linked behavior cannot be safely proven in a lightweight sandbox. Report that limitation instead of testing against the user's live account.

## 8. Report for a decision

Lead with the install recommendation. Then give concise findings ordered by severity and confidence.

Include:

- exact audited version/tag/commit, artifact, platform, install path, and date;
- whether malicious behavior or covert collection was found;
- a network/data-flow map showing endpoint, trigger, data, and whether it is required or optional;
- vulnerabilities with practical impact and fixed versions;
- release/provenance confidence;
- important positive controls such as encryption, sandboxing, private permissions, host allowlists, and rollback;
- limitations, including unreviewed transitive code and any omitted dynamic testing;
- a safer installation path or minimal mitigations.

Use source links pinned to immutable commits and put citations next to the supported finding. Never bury a blocking issue beneath general reassurance.

Suggested confidence language:

- **Confirmed:** directly demonstrated by source, artifact metadata, or a reproducible test.
- **Strong evidence:** several independent static checks agree, but runtime behavior was not observed.
- **Not established:** source-to-binary reproduction, exhaustive transitive review, or behavior requiring a live account was not proven.

End by stating explicitly whether anything was installed or executed and offer the next safe action only if it stays within the user's requested scope.
