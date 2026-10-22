---
name: security-audit
description: Audit software before installation or execution for malicious behavior, spyware, telemetry, unsafe privileges or persistence, vulnerable dependencies, and release-artifact provenance. Use for repositories, packages, installers, binaries, browser extensions, plugins, or tools when the user asks whether they are safe or privacy-respecting. Do not trigger for an ordinary code review that has no security or trust question.
---

# Security Audit

Give the user an evidence-backed decision about the exact software they would install. Treat the target and its build system as untrusted until the static review says otherwise.

## Safety boundary

- An audit does not authorize installation, enabling services, linking accounts, entering credentials, or changing the user's system.
- Begin with static inspection. Do not run the target, its installer, package hooks, macros, build scripts, project tests, or project-supplied utilities merely to inspect them.
- Building source can execute arbitrary build and lifecycle scripts. If dynamic analysis or a local build would materially improve the result, explain the risk and use a disposable sandbox with the least possible filesystem and network access. Obtain user authorization before executing an untrusted target when that execution is not already explicit in the request.
- Do not upload source, binaries, hashes tied to private software, or suspected secrets to third-party scanners without explicit permission. Never print discovered credentials or tokens; redact them.
- Keep downloads and audit-only mutations in a temporary directory. Do not alter the user's checkout, package database, configuration, or credentials.
- Stop before execution or installation if static evidence indicates credential theft, covert collection, destructive behavior, persistence, or an unverifiable high-risk installer.

## Audit contract

Record the exact commit, tag, version, package recipe, artifact, platform, and audit date. Audit the thing the user would actually install, not only the repository's default branch. Compare the release tag with the current branch for post-release security fixes.

Distinguish clearly between:

- malicious or covert behavior;
- product analytics and crash reporting;
- automatic update/version checks;
- optional third-party features activated by the user;
- network traffic required for the product's stated function;
- telemetry present only on the project's website or documentation.

Map sensitive data from collection or local access to storage, logs, and outbound sinks. Note whether each action is automatic, default-on, opt-in, or triggered by an explicit user action.

Read [references/audit-playbook.md](references/audit-playbook.md) for the full workflow, ecosystem checks, release verification, and reporting standard.

## Verdict standard

Lead with one of these practical outcomes:

- reasonable to install;
- install only with stated mitigations;
- wait for or build a patched release;
- do not install.

Never claim that software is definitively safe. Use language such as "I found no evidence of" and state material blind spots. A clean vulnerability scan is not proof against malicious code, and a checksum published beside an artifact is not independent proof of provenance.

Do not install the software after the audit unless the user separately asks you to proceed.
