# Forced determinism

> **Last change — 2026-07-14:** Device loss, a late start, or peer refusal can force fallback; each `mystery` belongs to one withdrawal.

Forced determinism occurs when the Boomerang path becomes unavailable and the
participants must wait for the normal, deterministic withdrawal period. The
known paths are device loss, a late start, and peer non-cooperation.

## Attack vectors

### 1. Loss of a Boomlet card

**Scenario:** If one card is lost, the protocol cannot use the Boomerang path
and must wait for the normal deterministic withdrawal period.

**Potential guard:** Keep a provisioned Boomletwo.

**Remaining vulnerability:** Boomletwo activation, revocation, and concurrent-use
prevention are not defined. The backup cannot be treated as an available
recovery device until that protocol exists; it can also fail, be lost, or be
destroyed.

**Rationale:** Losing two separately stored cards should be less likely than
losing one, provided that the holder stores the backup more securely.

### 2. Late withdrawal

**Scenario:** Each Boomlet samples a fresh `mystery` only when an approved
withdrawal enters `DIGGING`. The peers know the configured range but not the
five sampled values or their maximum, so they cannot know whether a late
ceremony will finish before a fallback milestone. Narrowing the range reveals
more about completion time. Allowing users to choose the range does not remove
the risk.

**Potential guards:**

- Add a flush mechanism.
- Make the Boomerang period long enough for timely rollover, supported by Niso
  notifications.

**Remaining vulnerabilities:**

- A static flush mechanism only postpones the same last-resort problem.
- Users may overlook the rollover requirement or its notifications.

### 3. Peer non-cooperation

**Scenario:** If one peer stops cooperating during withdrawal, all participants
must wait for the normal period.

**Guard:** The protocol assumes cooperation among all users, as does a 5-of-5
multisig. A 4-of-5 Boomerang path would weaken that commitment: four users could
bypass the fifth, so one honest user could no longer preserve the protocol's
guarantees.

**Remaining vulnerability:** Non-cooperation remains an open risk.
Reached peers must keep sending fresh pings and processing placeholders until
WT distributes a valid all-reached collection, so refusal can stall the
ceremony even after a peer reaches its own threshold.

## Assessment

### Options considered

1. **Immediately flush the funds into another Boomerang with a presigned
   transaction.** This only moves the last-resort problem to the next
   Boomerang.
2. **Use a third party for fast transfers during the Boomerang period.** The
   transaction cannot simply be presigned because the third party could publish
   it at will. Sending to another Boomerang raises further questions: how is the
   second Boomlet protected from being bypassed, and what state must it retain?
   A third party without cryptographic proof of constrained behavior introduces
   another trust problem.
3. **Use a long Boomerang period and a narrow uncertainty range.** Choose the
   values so that, for at least a target percentage of the Boomerang period, a
   withdrawal ceremony will not overlap the normal period. This is the only
   option used by the protocol.

### Existing safeguards

- Generate `mystery` once per withdrawal at `DIGGING` entry, retain it across
  retries in that ceremony, and erase it with active withdrawal state. A
  threshold inferred by WT cannot carry into a later withdrawal.
- Make the Boomerang period long relative to the uncertainty range.
- Notify users when they should roll funds into a new Boomerang setup.

### Unresolved proposal

Consider a third party that is cryptographically constrained to move funds into
a new setup without gaining independent spending authority, if such a function
can be designed.


## Earlier discussion

[Historical design discussion](forced_determinism_history.md)
