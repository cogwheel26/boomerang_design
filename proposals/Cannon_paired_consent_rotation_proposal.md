# Paired consent rotation proposal

[Exact messages and recovery rules](Cannon_paired_consent_rotation_messages.md)
and the [full low-level sequence](Cannon_paired_consent_rotation_sequence.puml)
specify the ceremony below. The choices are recorded in
[ADR 0009](../adr/0009-paired-consent-rotation.md) and
[ADR 0010](../adr/0010-niso-relayed-consent-rotation.md).

## Behavior

Boomlet and its designated inactive Boomletwo replace their consent set through
authenticated two-phase commit. The set remains five distinct countries from
the 193-entry `DURESS_DISPLAY_VOCABULARY`, unordered and stored as
`duress_consent_set: list<u16>`. The descriptor, logical peer identity, ST input
method, and setup-bound WT and SAR registrations remain intact. Rotation can run
between withdrawals, during `DIGGING` after commitment, and in later withdrawal
phases. A stalled withdrawal uses its retained phase for this eligibility check.

Every rotation MUST ask for the previous committed set through trusted ST.
A valid five-country mismatch MUST durably latch duress before Boomlet releases
any response. Correct and wrong answers proceed identically to fresh enrollment;
the previous-set answer classifies duress, while signed ST approval authorizes
rotation.

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

Both devices retain the current set and protected consent records. Active
withdrawal checkpoints stay on their source.

| State | Requirement |
| --- | --- |
| `consent_epoch` | Monotonic `u64` version of the committed set; initial epoch is 0. |
| `duress_latched` | Persistent Boolean; authenticated imports and recovery merge using OR. |
| `consent_state_seq` | Source-issued `u64`, advanced for each accepted previous-set answer and coordinator decision, regardless of classification; target mirrors authenticated advances. |
| `last_attempt_seq` | Protected attempt floor; prevents delayed authorization from reopening an aborted attempt. |
| `consent_quarantined` | Blocks ordinary withdrawal with the stored set while allowing previous-set comparison. |
| `committed_set_history` | Protected append-only history of committed sets, including the current set. |
| `rotation_journal` | Bound authorization, attempt, ST phases and nonces, accepted responses, candidate, prepare evidence, decision, and exact recovery messages. |
| `withdrawal_checkpoint` | Source-only protected pause record, active transaction binding, preserved ceremony state, outstanding SAR duties, and pending resume receipt. |

Initial and replacement backups inherit the replicated consent state. Atomic
writes and protected rollback floors are required; old signed records cannot
prove freshness.
Reserve bounded journal and history capacity before asking for the previous set.
Exhaustion, overflow, missing history, or uncertain storage integrity blocks
authority rather than discarding evidence.

Each physical device needs a protected management identity distinct from the
copied peer identity, authenticated to its setup and backup slot. Maintenance
signatures use separate domains and authorize only scoped consent transitions.

The normal-key-certified pair binding fixes both management keys, logical peer,
ST, and lifecycle generation. ST retains that binding and the setup identity.
History transfers use 32 fixed slots, including initial enrollment; after 31
successful rotations, another rotation is blocked by capacity exhaustion.

## Rotation ceremony

1. **Authorize and hold.** Niso relays encrypted messages as an untrusted host.
   ST retains its air gap, identifies the setup and device pair, and explicitly
   approves the nonce-bound rotation scope. It binds the retained pair certificate,
   next attempt sequence, predecessor consent epoch, and base consent state sequence.
   The certificate fixes setup, logical peer, physical endpoints, ST, lifecycle,
   and profile; signature domains distinguish operations. Both devices verify the
   ST signature and their stored pair certificate against retained public keys.
   Rotation requires no mnemonic or normal private key.
   Boomlet rechecks withdrawal eligibility and waits for ST to be available.
   It privately binds the review to its current withdrawal identity.
   After verifying that binding, the review nonce, predecessor, and storage
   capacity, Boomlet atomically records the checkpoint, OR-latches any current
   withdrawal duress, admits the attempt, advances the attempt floor, quarantines
   the predecessor, and sends encrypted `HOLD` carrying that approval.
   Boomletwo independently verifies the certificate, ST approval, inactive role,
   and predecessor state, durably quarantines its set and holds activation, then returns
   `HELD`. Boomlet persists that receipt and its OR merge of the target latch
   before issuing the previous-set prompt.

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
   excludes previous-set guesses. Candidate validation and bounded confirmation
   retries depend only on candidate and confirmation results, never the latch.
   Failure preserves quarantine and
   duress. Only exact resumption of the same recorded attempt may reuse its
   completed previous-set check. The candidate remains inactive.

4. **Prepare.** Boomlet freezes competing operations and durably records the
   candidate and encrypted `PREPARE` before sending. The candidate binds the
   authorization, attempt, predecessor, new epoch, set,
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
   remains inactive. Boomlet retains its rotation hold until it verifies and
   persists that receipt, then clears quarantine and reports completion. An active
   withdrawal resumes through the checkpoint and SAR gate below.

Only the committed new set can classify as safe, subject to the latch. The old
set stays invalidated; no overlap is allowed. A true latch permits ordinary
rotation completion.

## Rotation during a withdrawal

Pause local progress, new withdrawal ST input, signing, and fragment export.
Retain the same PSBT, identifiers, approvals, phase, mystery, counter, Ping
sequence, reached state, replay floors, and signing history. Preserve accepted
duress and continue servicing exact previously emitted messages and SAR receipts.
Outstanding unconsumed Pongs lose progress eligibility; their SAR duties remain.
A pending withdrawal country challenge is retired, and its replacement after
commit uses the new set and a fresh nonce.

After verified COMMITTED, resume the preserved ceremony in place, including
receipt updates recorded during the pause. Apply normal freshness and chain-view
checks; elapsed time grants no progress or deadline extension. A fresh Ping at
the next unused sequence carries current duress. Its exact SAR acknowledgment
must be durably consumed before further counter credit, new signing output, or
fragment export. This gate applies to either
duress value. WT returns that acknowledgment even after digging has terminated;
it authorizes no progress by itself.

Abort preserves quarantine and keeps the withdrawal paused. Later authorized
rotation can repair consent; ordinary withdrawal abandonment preserves replay
and rescue obligations. Already released signatures, fragments, placeholders,
and rescue activations retain their effects. The checkpoint stays on Boomlet;
consent commitment supplies no proof that Boomletwo can resume its withdrawal.

## Abort and recovery

Before durable commit, Boomlet may durably decide `ABORT`, advance its sequence,
and send the decision with its latest latch. Boomletwo persists the OR merge
and encrypted `ABORTED` receipt; Boomlet durably merges the returned state before
resolving the attempt. A target that missed `HOLD` still verifies authorization
through `ABORT_UNHELD`, which carries the original ST-signed approval. The target
verifies it against the stored pair certificate. Its sequence is base plus one
because no previous-set question has run. The target records the abort and quarantine, preventing delayed messages
from reviving it. Candidate material may be erased, but duress, history,
quarantine, replay floors, and required receipts remain. Another rotation
requires resolved participant records and fresh authorization. Abort preserves
predecessor quarantine.

| Interruption | Required action |
| --- | --- |
| Wrong answer recorded before transfer | Recover the source latch; target remains held until prepare or authenticated abort transfers it. |
| Target prepared, source decision unknown | Recover the durable source decision; no unilateral timeout decision. |
| Source committed, delivery or receipt lost | Retransmit exact commit or retrieve exact committed receipt; commit cannot become abort. |
| Conflicting evidence, rollback, missing journal, or permanent source loss | Block uncertain authority until authenticated decision and current state are recovered. |

Exact retries neither advance counters nor repeat acceptance or writes. Fresh
status queries and challenge replacements have reserved, bounded caches. Status
retrieval changes no consent state; only recovered decision or receipt evidence
can resolve a held state. ST restart retires unconsumed challenges and receives
a fresh nonce-bound resumption, preserving accepted duress. An unavailable
coordinator leaves unresolved participants held.

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
  diagnostics accessible to Niso, WT, or channel observers.

New envelopes use fresh IVs; retries reuse exact stored bytes. Authenticate
before decryption and expose uniform cryptographic errors. Each new withdrawal
placeholder retains its `approved_withdrawal_id` context and fresh IV. Preserve
existing in-flight bytes and exact SAR acknowledgment obligations.

Transaction review, unanimous approvals, digging, MuSig2 nonce safety, and
signing gates remain required. WT forwards every placeholder to the setup-bound
SAR. SPEC Sections 16.3–16.6 retain their exact-envelope acknowledgments, identical
durable processing, fixed deadlines, replay handling, and concealment rules.

## Activation and assumptions

Rotation starts outside a live MuSig2 exchange. Private fresh enrollment, trusted
endpoints, secure keys, and rollback-resistant storage remain assumptions.
A coercer who knows and dictates the correct previous
set can avoid this particular signal and observe the replacement.

ST approval permits consent rotation within the retained device pair. Device
replacement, rebinding, signing, and Boomletwo activation retain their separate
requirements. Someone controlling the paired trusted devices and ST can perform
unauthorized maintenance, including persistent duress latching or history
exhaustion.

Boomletwo activation independently requires enforceable source exclusion and
proof of the latest consent, replay, signing, and rescue state. Until both are
proved, the target stays inactive. Permanent source loss requires independent
proof. Legacy devices must enforce the same gates before participating.
