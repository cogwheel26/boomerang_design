# Paired consent rotation proposal

[Message contract](Cannon_paired_consent_rotation_messages.md) and
[complete sequence](Cannon_paired_consent_rotation_sequence.puml).
Decisions are recorded in [ADR 0009](../adr/0009-paired-consent-rotation.md) and
[ADR 0010](../adr/0010-niso-relayed-consent-rotation.md).

## Behavior

Boomlet and its designated inactive Boomletwo replace their unordered
five-country `duress_consent_set` through authenticated two-phase commit.
The descriptor, logical peer, ST input method, and WT and SAR registrations
remain intact. Rotation can run between withdrawals, during DIGGING after
commitment, and in later withdrawal phases. Stalled withdrawal uses its retained
phase. Rotation assumes no live MuSig2 exchange.

Every rotation MUST ask for the current committed set through trusted ST.
A valid mismatch MUST durably set the duress flag before any response, while
following the same enrollment and commit flow as a correct answer.

```text
under_duress := under_duress OR answer_is_wrong
user_is_in_duress := under_duress
```

Correct answers, further rotation, retries, and restart cannot clear the flag.
Later wrong withdrawal answers can still set it. Every subsequent commitment
and Ping carries the key-bearing SAR placeholder while the flag is true.

The flag lasts through withdrawal end and verified delivery to SAR. Between
withdrawals, it carries into the next one. Both devices OR-merge authenticated
flag transfers. Reset follows the paired completion rule below. A valid mistaken
answer can therefore cause false duress for that withdrawal.

Successful commit replaces the old set; it is then discarded. The candidate
must differ from the current set. Devices retain no historical sets or rotation
count. They cannot prevent later re-enrollment of an older, potentially exposed
set; private enrollment remains necessary.

## Protected state

| State | Requirement |
| --- | --- |
| `duress_consent_set` | Current committed five-country set; one candidate during rotation. |
| `under_duress` | Durable Boolean, initially false; OR-merged until authorized withdrawal-end reset. |
| `consent_freshness_token` | Shared random freshness token; consumed on every admitted attempt, including one that aborts. |
| `consent_quarantined` | Blocks withdrawal with the stored set while allowing rotation comparison and recovery. |
| `consent_rotation_state` | Current approval, input steps and nonces, candidate, prepares, decision, and exact recovery messages. |
| `paired_reset_pending` | Source records that a rotation flag was replicated; cleared after authenticated paired reset. |
| `withdrawal_checkpoint` | Source-only pause state, signing and replay history, SAR duties, and resume gate. |

Use atomic, rollback-resistant storage for the whole record. Random tokens do
not protect a restored storage snapshot. Reserve bounded storage for rotation,
checkpoint, reply-cache, and reset records before admission. Uncertain storage blocks
authority rather than discarding evidence.

Existing authenticated setup fixes the peer, backup and ST identities. Boomlet
retains the authorized backup public key; Boomletwo retains its original keypair
and imported setup state. Setup-bound control channels use those retained keys.
ST receives review details through its existing authenticated Boomlet channel.
The inactive backup's applet confines its copied Boomlet key to dormant state
and SAR-receipt verification
until authorized activation. Rotation requires no mnemonic or normal private key.

## Ceremony

1. **Authorize and hold.** Niso relays encrypted messages. ST displays the setup
   and device pair from Boomlet's authenticated review, then explicitly signs a
   fresh nonce-bound current freshness token. The approved review nonce identifies
   the attempt in subsequent messages.
   Boomlet verifies the retained pairing, ST signature, pending review and nonce,
   current token, withdrawal eligibility, and storage. It privately binds review
   to the current withdrawal.
   Admission atomically replaces the token with the approved nonce, checkpoints
   and pauses withdrawal, preserves accepted duress, sets quarantine and
   `paired_reset_pending`, and records HOLD before sending. Boomletwo verifies
   the approval, stored binding, inactive role, token, and terminal predecessor
   record, then consumes the token and persists HOLD. Boomlet consumes HELD and
   OR-merges its flag before prompting.

2. **Check the previous set.** A fresh ST challenge binds the approved rotation
   ID, input step, permutation, and prompt nonce. Boomlet accepts five valid
   distinct indices,
   compares against its current set, and atomically persists answer consumption,
   the flag, and a uniform CONTINUE result. A mismatch proceeds without
   correctness feedback or extra prompts. Malformed or stale input stalls.
   Exact retries recover the recorded successor.

3. **Enroll.** The user chooses a different five-country set and reproduces it
   in two fresh nonce-bound confirmations. At most three rounds run. Each round
   completes both confirmations before reporting its candidate result,
   regardless of the flag. The candidate remains inactive.

4. **Prepare.** Boomlet persists the candidate and PREPARE. Boomletwo verifies
   the admitted rotation ID and valid replacement, OR-merges the flag, and
   durably stores that candidate and PREPARED. The receipt identifies the exact
   PREPARE and merged flag. Boomlet verifies both, rejects a flag downgrade, and
   persists the same candidate. Prepared candidates are immutable; further
   country input, signing, and pairing changes remain held.

5. **Commit.** After both durable prepares, Boomlet atomically installs the
   candidate and records irrevocable COMMIT before sending. COMMIT identifies
   the exact PREPARED receipt. Boomletwo verifies it, atomically installs its
   prepared candidate, clears consent quarantine, and stores COMMITTED identifying
   the exact COMMIT. It remains inactive. Boomlet releases its hold only after
   durably consuming that receipt. The freshness token installed at admission
   remains current; completed predecessor and input material can be erased.

Fresh requests must match the protected current token. Admitted messages use
their rotation record's approved rotation ID and rotation phase. Terminal control
duplicates recover cached results without prompts, writes, or repeated flag
merging. A successor retires the preceding attempt's input and candidate records.

## Withdrawal pause and flag reset

Preserve the same PSBT, identifiers, approvals, phase, mystery, counter, Ping
sequence, reached state, signing nonce history, and replay memory. Pause new
progress, withdrawal ST input, signing output, and fragment export. Continue
servicing exact emitted messages and SAR receipts. Retire unsent Pings and
unconsumed Pongs; their reserved sequences and SAR duties remain protected.
Replace retired country input after commit with the new set and a fresh nonce.

After COMMITTED, resume the checkpoint in place under ordinary freshness and
chain-view gates. A fresh Ping at the next unused sequence carries the flag.
Its exact SAR acknowledgment must be consumed before further counter credit,
signing output, or fragment export. The resume gate is bound to the current
freshness token; an earlier receipt cannot clear it. Neither receipt nor elapsed
time credits progress or extends a deadline. WT returns receipts after digging
termination and refreshes reached evidence for ordinary signing revalidation.

At withdrawal end, freeze further input and emit a fresh final Ping for either
flag value. Consume its exact SAR acknowledgment before clearing the flag.
If `paired_reset_pending` is true, Boomlet sends an encrypted, identity-signed
FINISH containing the current token, a fresh next token, ending withdrawal ID,
and final SAR receipt. Boomletwo verifies the source statement, token, terminal
state, and SAR evidence; a true copied flag requires acknowledgment of the
key-bearing placeholder. It atomically clears the flag, installs the next token,
and stores FINISHED. Boomlet clears its flag and pending reset only after consuming
that receipt. Both classifications use the same exchange and release rules.

Missing FINISHED blocks another withdrawal or rotation; exact FINISH retries
recover it. Where no rotation flag was replicated, reset is local after withdrawal
end and exact SAR delivery. Reset cannot undo an existing SAR activation.
Reboot or abandonment without delivery preserves the flag and rescue duties.
Idle rotation clears only through the next withdrawal's completion.
Unresolved or quarantined rotation cannot reset the flag.

## Abort, recovery, and concealment

Before COMMIT, Boomlet may record ABORT with its latest flag. Boomletwo durably
OR-merges it and returns ABORTED; Boomlet persists that merge before resolving.
If HOLD was unacknowledged, ABORT_UNHELD carries the original ST approval and
consumes the target's predecessor token if unseen. Another attempt requires
resolved records, the prior receipt, and fresh approval. Abort preserves consent
quarantine and the flag.

| Interruption | Required action |
| --- | --- |
| Wrong answer recorded before transfer | Recover the source flag; target stays held until prepare or authenticated abort transfers it. |
| Target prepared, source decision unknown | Retransmit exact PREPARED; source returns its recorded COMMIT or ABORT, otherwise both stay held. |
| COMMIT or receipt lost | Retransmit exact COMMIT or recover COMMITTED; commit cannot become abort. |
| Final SAR receipt or FINISHED lost | Retain the flag and exact delivery or reset record; retry without new input. |
| Rollback, conflicting evidence, or permanent source loss | Block uncertain authority until current state and decision are independently proved. |

Device recovery retransmits retained control envelopes through their ordinary
handlers. Source RESUME returns its pending control message or ST input; target
RESUME returns its latest receipt. Exact duplicates recover recorded successors
without new input or repeated flag merging. Prepared devices never decide from
timeout.

ST recovery retains one exact encrypted reply and up to eight accepted query
digests per attempt. The current query's retry returns that reply; superseded
queries are rejected without replacing input. Fresh recovery atomically records
its digest, reply, and any replacement challenge, preserving accepted answers,
the flag, and decisions. ST accepts only replies matching its outstanding query
nonce. The cache and query budget survive restart.

Encrypt sets, flags, signatures, and receipts with SPEC's
directional CBC-CMAC channels. Verify authentication before decryption. Bind
operations to setup, physical pair, token, input step, and exact request.
Use fresh IVs for new envelopes and stored bytes for retries.

Correct and wrong previous answers and either flag value MUST have identical
prompts, message counts, lengths, routing, bounded retries, durable processing,
trusted fixed deadlines, and permitted failures. Public status, logs, metrics,
and diagnostics reveal no classification. Recovery and reset follow the same
rules. Preserve SPEC Sections 16.3–16.6 SAR acknowledgment and concealment promises.

ST approval permits only consent rotation within the fixed pair. Control of the
trusted paired devices and ST permits unauthorized maintenance or forced duress.
A coercer who knows and dictates the correct set can avoid that check's signal.
Device replacement, rebinding, transaction approval, digging, signing, and
Boomletwo activation keep their separate requirements. Activation still requires
enforceable source exclusion and proof of latest consent, signing, replay, and
rescue state; a rotation or reset receipt supplies no activation authority.
