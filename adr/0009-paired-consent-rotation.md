# ADR 0009. Paired Consent Rotation With Durable Acknowledgment

- **Status:** Proposed
- **Recorded:** 2026-10-07

## Context

Boomlet is the active trusted device; Boomletwo is its designated inactive
backup. Both store the user's unordered five-country consent set. A paired
trusted ST device handles user input. Observation can disclose that answer.
Replacement must invalidate the predecessor on both devices while retaining one
memorized answer, the existing descriptor, and service registrations.

## Decision

Retain the unordered set of five distinct countries. Boomlet records an
authenticated, irrevocable UPDATE installing the replacement and duress flag.
Boomletwo installs the set, OR-merges the flag, and returns a signed, encrypted
ACK bound to the exact UPDATE only after durable storage.

Both devices are held before the previous-set check. Trusted ST obtains that
answer and two fresh enrollment confirmations. A valid mismatch durably sets
duress before any reply and completes the same flow. Correct and wrong answers
have identical observable behavior, with sets and duress encrypted.

Boomlet remains held until it durably consumes the ACK and required SAR receipt.
Cancellation is permitted only before UPDATE is recorded. Lost messages recover
through exact UPDATE and cached ACK retries.

## Rationale

Boomlet makes the authorized replacement decision; the inactive backup stores
it. Durable acknowledgment provides the evidence needed before withdrawal
resumes, while keeping one current decision and its recovery messages.
The hold prevents either device from acting on uncertain consent state.
This preserves the existing interaction without an external freshness authority.

## Consequences

Both devices must participate, and storing the secret twice increases correlated
exposure. Recovery requires rollback-resistant state and exact message retries.
An unavailable backup blocks completion after UPDATE; Boomlet cannot roll back
the installed replacement. Abort preserves quarantine and duress.

Rotation may pause withdrawal during digging after commitment or in later phases,
preserving progress, signing history, and SAR duties. Resumption requires ACK
and exact SAR acknowledgment. The duress flag survives correct answers until
withdrawal end and acknowledged delivery, with paired reset when replicated;
idle rotation carries it into the next withdrawal. Past sets are discarded, so
later re-enrollment of an older exposed set remains possible.

Boomletwo stays inactive. Activation requires proof that the source can no
longer act and the backup has the latest consent, replay, signing, and rescue
state.

## Rejected Alternatives

- **Enroll the same set separately on each device:** avoids transferring the set
  but repeats input and exposure opportunities; private equality checking still
  cannot prove durable installation.
- **Retire the backup before local rotation:** requires enforceable exclusion and
  leaves recovery without an eligible backup until replacement.
- **Derive sets from a shared root and witnessed epoch:** adds an external
  freshness and availability dependency; root compromise exposes covered epochs.
- **Store encrypted recovery sets with an epoch witness:** supports an offline
  backup but adds storage, witness availability, and recovery-key dependencies.
- **Use one-time answers or private randomized cues:** changes the reusable
  interaction and adds consumption state or a private channel assumption.
- **Require independent rescue review for every withdrawal:** introduces guardian
  clearance and escalation, changing rescue authority and concealment guarantees.
