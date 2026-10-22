# Privacy and data inventory

What this app holds about people, where it goes and how long it stays. The `privacy-check` skill
keeps this file true: every merge to `main` that changes personal data, logging, storage or third
parties updates it in the same commit.

Last full check: <date> at <commit> (`privacy-check` baseline).

## Principles

- Collect the minimum the feature needs; every new personal field is an explicit decision recorded here.
- No tracking of individuals. Usage and error insight is anonymous and aggregate.
- Nothing personal goes to a third party unless it's listed below with its reason.

## Personal data held

| Data | Where (table/column, file, log) | Why | Who can see it | Retention | Deleted by |
| --- | --- | --- | --- | --- | --- |
| | | | | | |

## Logs

| Log | Contents | Personal data? | Where / readable by | Retention |
| --- | --- | --- | --- | --- |

## Client-side storage

| Key | Holds | Lifetime | Cleared on sign-out? |
| --- | --- | --- | --- |

## Third parties

| Service | Receives | Why | Self-hostable? |
| --- | --- | --- | --- |

## Usage and error telemetry

What is counted, at what granularity, where it's stored, retention. "None" is a valid answer.

## Secrets

Names and locations only. Rotation status belongs in the private register.

| Secret | Lives in | Rotate when |
| --- | --- | --- |

## Open findings

Not kept in this repository. Unfixed findings and secret rotation status live in the
maintainer's private register until they're fixed, so this file never advertises an open hole.

## Accepted risks

Things we chose to live with, and why.
