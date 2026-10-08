# ADR 0009. Paired Consent Rotation Through Two-Phase Commit

- **Status:** Proposed
- **Recorded:** 2026-10-07

## Context

Boomlet is the active trusted device; Boomletwo is its designated inactive
backup. Both store the user's unordered five-country consent set. A paired
trusted ST device handles user input. Observation can disclose that answer.
Replacement must invalidate the predecessor on both devices while retaining one
memorized answer, the existing descriptor, and service registrations.

## Decision

Retain the unordered set of five distinct countries. Boomlet coordinates
authenticated two-phase commit of the fresh set, epoch, history, and persistent
duress state with Boomletwo.

Both devices durably prepare the same candidate before Boomlet records an
irrevocable commit. Boomlet resumes withdrawal only after consuming Boomletwo's
durable commit receipt. Unresolved participants remain held pending authenticated
decision evidence.

Every rotation asks for the previous committed set through ST, then enrolls a
fresh set with two confirmations. A valid mismatch durably latches duress before
any reply and follows the same enrollment flow. Prepare and abort transfer that
latch through encrypted, authenticated messages and merge it using OR. It never
clears within the setup and applies to future commitments and Pings. Correct and
wrong answers have identical observable flows; sets and duress remain encrypted.

## Rationale

Paired commitment coordinates both stored copies without changing the user's
consent method or adding an external epoch authority. Safety takes priority over
availability when the decision is uncertain. Two-phase commit can block when
its coordinator fails; this is an accepted cost
([Gray and Lamport](https://www.microsoft.com/en-us/research/wp-content/uploads/2016/02/tr-2003-96.pdf)).

## Consequences

Both devices must participate, and storing the secret twice increases correlated
exposure. Recovery needs protected journals, rollback floors, and exact decision
and receipt retries. Abort keeps the previous set unusable for withdrawals and
preserves latched duress. Rotation can pause an active withdrawal during digging
after commitment or in later phases, preserving mystery, progress, signing history,
and SAR duties. Resumption requires the commit receipt and a fresh Ping's exact
SAR acknowledgment. Rotation leaves Boomletwo inactive; activation requires proof
that the source can no longer act and the backup has the latest consent, replay,
signing, and rescue state.

## Rejected Alternatives

- **Enroll the same set separately on each device:** avoids transferring the set
  but repeats input and exposure opportunities; private equality checking still
  cannot prove durable commitment.
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
