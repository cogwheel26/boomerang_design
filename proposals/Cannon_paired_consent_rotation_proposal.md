# Paired consent rotation proposal

[Exact messages and recovery rules](Cannon_paired_consent_rotation_messages.md)
and the [full low-level sequence](Cannon_paired_consent_rotation_sequence.puml)
specify the ceremony below.

## Behavior

Boomlet and its designated inactive Boomletwo replace their consent set through
authenticated two-phase commit. The set remains five distinct countries from
the 193-entry `DURESS_DISPLAY_VOCABULARY`, unordered and stored as
`duress_consent_set: list<u16>`. The descriptor, logical peer identity, ST input
method, and setup-bound WT and SAR registrations remain intact.

Every rotation MUST ask for the previous committed set through trusted ST.
A valid five-country mismatch MUST durably latch duress before Boomlet releases
any response. Correct and wrong answers proceed identically to fresh enrollment;
the previous-set answer classifies duress, while normal-key authorization permits
maintenance.

```text
duress_latched = duress_latched OR (answer != previous_committed_set)
user_is_in_duress = duress_latched OR current_check_is_duress
```

The latch survives correct answers, rotation, abort, restart, withdrawal
completion, and device replacement. It has no clearing operation within the
setup. Only initial enrollment into a new setup initializes false. A mistaken
valid answer therefore causes persistent false duress; careful trusted prompts
and private, unhurried input mitigate that risk.

Every future duress-bearing commitment and Ping uses `doxing_key_for_sar` when
`user_is_in_duress` is true, otherwise 32 zero bytes. A true latch applies from
the first commitment of each later withdrawal, even after ceremony state resets.

## Protected state

Both devices retain the current set and:

| State | Requirement |
| --- | --- |
| `consent_epoch`, `consent_commit_id` | Monotonic `u64` epoch and fresh 32-byte commit identifier; initial epoch is 0. |
| `duress_latched` | Persistent Boolean; authenticated imports and recovery merge using OR. |
| `consent_state_seq` | Source-issued `u64`, advanced for each accepted previous-set answer and coordinator decision, regardless of classification; target mirrors authenticated advances. |
| `last_attempt_seq`, `previous_decision_envelope_digest` | Protected attempt floor and last resolved decision digest; prevent delayed authorization from reopening an aborted attempt. |
| `consent_quarantined` | Blocks ordinary withdrawal with the stored set while allowing previous-set comparison. |
| `committed_set_history` | Protected append-only history of committed sets, including the current set. |
| `rotation_journal` | Bound authorization, attempt, ST phases and nonces, accepted responses, candidate, prepare evidence, decision, and exact recovery messages. |

Initial and replacement backups inherit this state. Atomic writes and protected
rollback floors are required; old signed records cannot prove freshness.
Reserve bounded journal and history capacity before asking for the previous set.
Exhaustion, overflow, missing history, or uncertain storage integrity blocks
authority rather than discarding evidence.

Each physical device needs a protected management identity distinct from the
copied peer identity, authenticated to its setup and backup slot. Maintenance
signatures use separate domains and grant no signing, activation, key-export,
or rescue-cancellation authority.

The normal-key-certified pair binding fixes both management keys, logical peer,
ST, and lifecycle generation. ST retains that binding and the setup identity.
History transfers use 32 fixed slots, including initial enrollment; after 31
successful rotations, another rotation is blocked by capacity exhaustion.

## Rotation ceremony

1. **Authorize and hold.** Rotation runs offline in Iso, which signs normal-key
   authorization and relays encrypted messages between the devices. ST retains
   its air gap and identifies the setup and device pair. Authorization binds protocol version,
   operation, setup, logical peer, physical source and target, lifecycle
   generation, predecessor epoch and commit identifier, proposed epoch, and
   fresh 32-byte `rotation_id`. Both devices verify it against their stored
   normal public key. Boomlet must have no active or stalled withdrawal,
   outstanding check, signing session, fragment handoff, or unresolved SAR duty.
   After verifying the nonce-bound ST review and reserving storage, it advances
   the attempt floor, quarantines the predecessor, and sends encrypted
   `HOLD`. Boomletwo verifies its inactive role and predecessor, durably
   quarantines its set and holds activation, then returns `HELD`. Boomlet
   persists that receipt and its OR merge of the target latch before issuing
   the previous-set prompt.

2. **Check the previous set.** ST asks without displaying the answer. Boomlet
   issues a fresh nonce-bound country challenge tied to the attempt, predecessor,
   device pair, and phase. It validates authentication, nonce, phase, five
   distinct indices, and ranges, then compares against the committed predecessor,
   even when quarantined or already latched. It atomically records response
   consumption, sequence, latch, next phase, and uniform reply before release.
   A valid mismatch continues without correctness feedback, refusal, extra
   prompts, or retry-until-correct. Malformed or stale responses leave the
   ceremony held. Exact retries recover the recorded result; an unconsumed
   challenge lost on restart is replaced with a fresh one.

3. **Enroll.** The user selects a fresh set and reproduces it in two confirmations,
   each with a fresh permutation, nonce, and phase. At most three enrollment
   rounds run; each performs both confirmations before reporting the candidate
   result. Both devices enforce non-reuse against committed history, which
   excludes previous-set guesses. Candidate
   validation and bounded confirmation retries depend only on candidate and
   confirmation results, never the latch. Failure preserves quarantine and
   duress. Only exact resumption of the same recorded attempt may reuse its
   completed previous-set check. The candidate remains inactive.

4. **Prepare.** Boomlet freezes competing operations and durably records the
   candidate and encrypted `PREPARE` before sending. The candidate binds the
   authorization, attempt, predecessor, new epoch and commit identifier, set,
   complete history with the new set appended, source sequence, and latch.
   Boomletwo verifies these and atomically persists its prepared state, activation
   hold, and encrypted `PREPARED` receipt. Its latch becomes
   `local_duress_latched OR source_duress_latched` immediately. The receipt
   binds the exact request and merged candidate. Boomlet verifies it and durably
   prepares that same tuple, inheriting any true target latch. No new check,
   withdrawal, signing, or conflicting lifecycle transition may intervene.

5. **Commit.** After both durable prepares, Boomlet atomically records irrevocable
   `COMMIT`, installs the merged tuple, and stores the encrypted decision before
   sending it. The new epoch is predecessor plus one; both committed records use
   `final_consent_state_seq = source_consent_state_seq + 1`.
   Boomletwo verifies the decision against its prepared record, atomically installs
   the same tuple and stores `COMMITTED`. It resolves its rotation hold but
   remains inactive. Boomlet retains its withdrawal hold until it verifies and
   persists that receipt, then clears quarantine and reports completion.

Only the committed new set can classify as safe, subject to the latch. The old
set stays invalidated; no overlap is allowed. A true latch permits ordinary
rotation completion.

## Abort and recovery

Before durable commit, Boomlet may durably decide `ABORT`, advance its sequence,
and send the decision with its latest latch. Boomletwo persists the OR merge
and encrypted `ABORTED` receipt; Boomlet durably merges the returned state before
resolving the attempt. A target that missed `HOLD` still verifies authorization
through `ABORT_UNHELD`, which carries the original pair certificate and nested
authorization. Its sequence is base plus one because no previous-set question
has run. The target records the abort and quarantine, preventing delayed messages
from reviving it. Candidate material may be erased, but duress, history,
quarantine, replay floors, and required receipts remain. Another rotation requires resolved
participant records and fresh authorization. Abort never restores predecessor
withdrawal.

| Interruption | Required action |
| --- | --- |
| Wrong answer recorded before transfer | Recover the source latch; target remains held until prepare or authenticated abort transfers it. |
| Target prepared, source decision unknown | Recover the durable source decision; no unilateral timeout decision. |
| Source committed, delivery or receipt lost | Retransmit exact commit or retrieve exact committed receipt; commit cannot become abort. |
| Conflicting evidence, rollback, missing journal, or permanent source loss | Block uncertain authority until authenticated decision and current state are recovered. |

Exact retries neither advance counters nor repeat acceptance or writes. Fresh
status queries and challenge replacements have reserved, bounded caches. Status
retrieval changes no consent state; only recovered decision or receipt evidence
can resolve a held state. ST restart retires unconsumed
challenges and receives a fresh nonce-bound resumption, preserving accepted duress.
Two-phase commit can block after coordinator failure, as
described by Gray and Lamport in
[*Consensus on Transaction Commit*](https://arxiv.org/abs/cs/0408036).
If the source is destroyed before transferring its latch, the target hold
prevents false-safe activation; delivery requires recovering the protected state.

## Concealment and withdrawal protection

Use SPEC's canonical encoding, directional channel keys, and CBC-CMAC
encrypt-then-MAC. Inter-device contexts distinguish each operation and bind the
setup; authenticated contents bind attempt, predecessor, physical endpoints,
lifecycle generation, and phase. ST flows use distinct phase contexts and fresh
nonces. Receipts bind exact encrypted requests and are signed inside
recipient-bound encryption. Keep sets, latch, history, and plaintext-dependent
hashes or signatures encrypted to prevent offline guessing.

Correct and wrong previous-set answers, and either latch value, MUST have:

- Identical prompts, message counts, types, lengths, framing, routing, completion
  status, and bounded retry policy. Pad history and records to fixed profile
  limits; expose no previous-answer correctness bit, including on ST.
- Identical bounded comparison and durable-write paths, queues, fixed response
  release deadlines, and failure behavior, including when the latch is already
  true. Deadlines must exceed measured worst-case work.
- No classification-dependent logs, metrics, status, backup inspection, or
  diagnostics accessible to Iso, Niso, WT, or channel observers.

New envelopes use fresh IVs; retries reuse exact stored bytes. Authenticate
before decryption and expose uniform cryptographic errors. Each new withdrawal
placeholder retains its `approved_withdrawal_id` context and fresh IV. Preserve
existing in-flight bytes and exact SAR acknowledgment obligations.

Transaction review, unanimous approvals, digging, MuSig2 nonce safety, and
signing gates remain required. WT forwards every placeholder to the setup-bound
SAR. SPEC Sections 16.3–16.6 retain their exact-envelope acknowledgments, identical
durable processing, fixed deadlines, replay handling, and concealment rules.

Maintenance preserves pending rescue duties and introduces no standalone SAR
notification. A latched signal reaches SAR through later ordinary withdrawal
traffic; without that traffic, persistence alone proves no delivery or rescue.

## Limits and adoption

Private fresh enrollment, trusted endpoints, secure keys, and rollback-resistant
storage remain assumptions. A coercer who knows and dictates the correct previous
set can avoid this particular signal and observe the replacement. Physical input
observation, compromised endpoints, and SAR revealing a signal fall outside
communication concealment. Rotation alone cannot repair extracted keys.

Boomletwo activation independently requires enforceable source exclusion and
proof of the latest consent, replay, signing, and rescue state. A rotation
receipt proves only that rotation. Loss reports, timeouts, normal-key signatures,
and old snapshots cannot establish current eligibility. If Boomlet is permanently
offline, proof cannot depend on contacting it; absent proof, the target stays
inactive. Fresh rotation by a replacement uses its designated inactive successor
and still asks for the previous set.

The message contract fixes typed payloads, domains, contexts, capacity, and retry
limits. Adoption requires canonical vectors and measured timing constants with
trusted device timers; host timing cannot satisfy concealment.
Legacy devices capable of bypassing these gates must be excluded. Validate:

- Every write and message boundary under crash, replay, loss, reordering,
  rollback, conflicting attempts, and stale backup activation.
- Wrong-answer persistence through successful rotation, failed confirmation,
  abort, restart, imports, and later commitments and Pings, including a true
  target latch merged back to the source.
- Equal safe and duress observations across traffic, timing, storage, errors,
  status, and telemetry; transcript guessing and substitution resistance;
  bounded resource use and retained SAR obligations.

These requirements need model, implementation, and hardware evidence before
adoption. Update SPEC, lifecycle requirements, security models, an ADR, and
protocol source diagrams when adopted.
