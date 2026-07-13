# Forced determinism

> **Last change — 2026-07-13:** Moved the historical discussion to a separate note; the current arguments and mitigation are unchanged.

Forced determinism occurs when the Boomerang path becomes unavailable and the
participants must wait for the normal, deterministic withdrawal period. The
known paths are device loss, a late start, and peer non-cooperation.

## Attack vectors

### 1. Loss of a Boomlet card

**Scenario:** If one card is lost, the protocol cannot use the Boomerang path
and must wait for the normal deterministic withdrawal period.

**Potential guard:** Keep a backup Boomlet.

**Remaining vulnerability:** The backup can also fail, be lost, or be broken.

**Rationale:** Losing two separately stored cards should be less likely than
losing one, provided that the holder stores the backup more securely.

### 2. Late withdrawal

**Scenario:** Peers do not know the exact `mystery` values in their cards.
Each value is sampled within the limits set by the Boomerang parameters, so the
peers cannot know the last safe time to begin withdrawal. Narrowing the range
would reveal more about when the normal period effectively begins. Allowing
users to choose the range does not remove the risk.

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

## Present approach

### Ideas considered

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
   presently viable option.

### Current mitigation

- Make the Boomerang period long relative to the uncertainty range.
- Notify users when they should roll funds into a new Boomerang setup.

### Possible future work

Consider a third party that is cryptographically constrained to move funds into
a new setup without gaining independent spending authority, if such a function
can be designed.

---

## Earlier discussion

[Historical design discussion](forced_determinism_history.md)
