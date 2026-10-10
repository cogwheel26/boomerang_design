# Paired consent rotation message contract

The [proposal](Cannon_paired_consent_rotation_proposal.md) and
[complete sequence](Cannon_paired_consent_rotation_sequence.puml) use these proposed
extensions to SPEC. They remain unadopted wire types. Canonical encoding, BIP340,
directional ECDH keys, and CBC-CMAC follow SPEC Sections 8–9. Tuple items have the
exact order and types below. Unknown versions, operations, enum values, trailing
bytes, and alternative encodings fail before semantic use.

## Pairing and attempt identity

```text
Review = (
  setup_instance_id: bytes32,
  backup_boomlet_pubkey: bytes33,
  rotation_request_with_nonce: MessageWithNonce<bytes32>
)
```

Existing setup uses the normal-key-authorized backup request, authenticated state
transfer, and signed `BackupDone` to establish the fixed pair. Boomlet retains the
accepted backup public key; Boomletwo retains the imported setup, source and ST
identities. Control envelopes bind the retained setup ID and paired keys.
Require distinct source and backup keys, including their x-only representations.
Rotation messages cannot replace the pairing or public keys.

Boomletwo retains its original keypair through import and uses it for target
messages. Until authorized activation, its applet permits the copied Boomlet key
only for SAR-receipt verification. Protected role and key selection survive
restart and cannot be chosen by a host. The inactive backup cannot originate
source rotation, withdrawal, or ST messages or expose arbitrary signing or
encryption with the copied key.

Provision the same fresh random 32-byte `consent_freshness_token` on both devices.
BEGIN_REVIEW creates `consent_rotation_request_with_nonce` with that token as
content and a fresh review nonce distinct from it. ST signs that exact object.
The approved review nonce is `consent_rotation_id` in every later rotation
payload. On authorized admission, both devices atomically replace their token
with that nonce and retain the original approval in `consent_rotation_state`.
This consumes the predecessor even if the attempt aborts.
Authorized pairing changes retire pending reviews and provision a fresh shared
token; tokens are never shared across setups or pairs.

A fresh HOLD requires a matching predecessor token and a terminal previous
rotation record. Exact recorded approvals take the recovery path before fresh
admission checks; another approval for that predecessor conflicts. Later handlers
match the recorded rotation ID and rotation phase, rather than the consumed
predecessor token.
Terminal control duplicates return cached results without writes, prompts, or latch
merging. Superseded attempts are stale. Random tokens require atomic,
rollback-resistant storage for the consent set, flag, and rotation record.

The source privately binds its pending review to the current withdrawal identity
or absence of one. Starting, replacing, completing, or abandoning a withdrawal
retires the review. Admission rechecks eligibility and checkpoints the latest
withdrawal state. Target imports no withdrawal checkpoint. Source consumes the
preceding decision receipt before admitting another attempt.

## Duress flag

Both devices store `under_duress: bool`, initially false. Every accepted valid
wrong answer, including the previous-set check, updates the source atomically:

```text
under_duress := under_duress OR answer_is_wrong
user_is_in_duress := under_duress
```

Correct answers, confirmation rounds, rotation, retries, and restart cannot clear
the flag. Authenticated state transfers OR-merge it. It governs subsequent
commitments and Pings through the end of the withdrawal. A flag set between
withdrawals carries into the next one. Withdrawal end permits the reset below
only after exact SAR acknowledgment; abandonment cannot erase an undelivered
signal. Enrollment confirmation failures are not duress answers.

Each admitted rotation sets source `paired_reset_pending=true`, regardless of
classification. It survives abort and restart until the paired reset completes.
The old set remains available for comparison during the attempt; successful
commit replaces it. Erase predecessor copies and completed country-input material
after terminal evidence is durable. Retain no archive of past sets.

## Trusted review and country input

Niso relays device-encrypted envelopes unchanged. ST retains its air gap and
supplies explicit signed approval. Rotation requires no mnemonic, passphrase, or
normal private key.

Local selectors are 41 BEGIN_REVIEW with empty tuple input, returning
one review envelope; 42 SUBMIT_REVIEW with one approval envelope, returning
encrypted HOLD; 43 reserved and rejected; 44 REQUEST_CANCEL with empty input;
and 45 RESUME on either device with empty input, returning its retained next
outbound envelope. Source may return control or ST input; target returns its
latest receipt. Local requests supply no authority themselves.

BEGIN_REVIEW requires no unresolved rotation, FINISH, or withdrawal teardown,
and a free ST input session. An active withdrawal qualifies during DIGGING after
commitment and in later phases; a stalled withdrawal uses its retained phase.
Commit-collection and SAR checks and one-time mystery initialization precede DIGGING. An early
request cannot pause or advance withdrawal. One volatile review is pending;
state loss before admission requires fresh review.

Source derives `Review` metadata from protected setup state and sends it through
its existing paired ST channel. ST authenticates that source and displays consent
replacement, setup, and source and backup identities, then explicitly approves.
It signs the exact `rotation_request_with_nonce` under
`Boomerang/consent_rotation/v1/st_review`.
ST durably retains the approved rotation ID before releasing approval and keeps
it across restart for UI recovery.

SUBMIT_REVIEW verifies the retained pairing, ST signature, exact pending token
and nonce, current predecessor token, private withdrawal binding, eligibility,
and storage reservation. Before releasing HOLD, source atomically persists the
approval, rotation record, consumed predecessor, checkpoint and pause, quarantine,
`paired_reset_pending=true`, and any already accepted withdrawal duress.
Exact approval retries recover HOLD or the terminal result without admission
again. An older approval cannot reopen a terminal or superseded attempt.

HOLD carries `SignedMessage<MessageWithNonce<bytes32>>`.
Target verifies the ST signature with its retained ST public key and checks the
setup-bound paired channel, inactive role, predecessor token, and rotation record
admission rules. It consumes that token and persists quarantine and activation
hold before HELD. Source persists HELD and its OR merge before asking for the
previous set. Neither host timestamps nor a rotation count establish freshness.

ST approval authorizes rotation only within the fixed pair. Device replacement,
rebinding, signing, and Boomletwo activation retain their separate requirements.

```text
Check = (consent_rotation_id: bytes32, enrollment_round: u8, input_step: u8, space: DuressCheckSpace)
Answer = (consent_rotation_id: bytes32, enrollment_round: u8, input_step: u8, selection: DuressSignalIndex)
UiResult = (consent_rotation_id: bytes32, enrollment_round: u8, result: u8)
PendingConsentInput = (input_pending: bool, enrollment_round: u8, input_step: u8, nonce: bytes32, space: DuressCheckSpace)
```

Challenges and answers use `MessageWithNonce<Check>` and
`MessageWithNonce<Answer>`. Space is a permutation of integers 1–193. ST displays
five independently shuffled columns and returns five distinct original indices.
Input step is 1 previous set, 2 selection, 3 first confirmation, or 4 second
confirmation. Enrollment round is 0 for the previous set and 1–3 for enrollment.
Require the exact rotation ID, enrollment round, input step, and outstanding
prompt nonce. Each input step uses a fresh nonce and permutation.

Before sending, persist the input step, nonce, permutation, and exact challenge
bytes.
Accepted answers atomically consume the nonce and store their response digest,
flag update, and cached successor. Restart recovers that record. An unconsumed
challenge may instead be retired and replaced; its retired nonce cannot satisfy
another input step. Accepted-response retries recover the successor without another
comparison, prompt, or write.

ST accepts challenges and results only for its retained approved rotation ID.
It retains the display maps and selections for one
`(consent_rotation_id, enrollment_round, input_step, nonce)` session. Before
answering, duplicates preserve that session. After answering, duplicates resend its exact cached
encrypted answer. Conflicting content at the same nonce is rejected. ST state
loss requires authenticated UI recovery.

The previous answer always yields UiResult 0 CONTINUE. Compare all five values
even when the flag is true; persist `previous_set_checked=true`, the flag, response
consumption, and uniform result before release. A valid mismatch proceeds through
the same enrollment flow.

Each enrollment round completes selection and both confirmations before reporting
1 RETRY or 2 READY. READY requires five valid distinct sorted countries, different
from the current committed set, and both confirmations matching. Candidate
validity never depends on the flag. After round 3 failure, source decides ABORT.
Authentication or encoding failures stall the input step rather than classify duress.
There is no lifetime non-reuse check.

UI results echo the answered nonce; round results echo the second-confirmation
nonce. Terminal results are 3 COMPLETE or 4 ABORTED, anchored to the latest
outstanding or accepted ST nonce, or review nonce if no country prompt ran.
ST retains the attempt and prompt nonces until terminal delivery. After ST state
loss, fresh authenticated status is required before displaying a terminal result;
an old unsolicited result cannot attach to another review.

Before COMMIT, cancellation requires ST approval of a fresh
`MessageWithNonce<bytes32>` containing the rotation ID under
`Boomerang/consent_rotation/v1/st_cancel`.
Source retires pending country input before issuing the persisted cancellation
challenge. Repeated REQUEST_CANCEL recovers that challenge without allocating
another nonce. Acceptance atomically consumes it and records cancellation.
Accepted duress survives; no cancellation can alter durable COMMIT.

## Candidate and control messages

```text
Candidate = (
  consent_rotation_id: bytes32,
  replacement_consent_set: list<u16>,  // exactly 5, ascending, distinct
  under_duress: bool
)
```

Define `EH(E) = sha256(canonical_encode(E))` for an encrypted envelope.
Keep all flag-bearing content and receipts encrypted.

| Operation | Exact signed content tuple |
| --- | --- |
| `hold` | `(authorization: SignedMessage<MessageWithNonce<bytes32>>)` |
| `held` | `(consent_rotation_id: bytes32, request_digest: bytes32, under_duress: bool)` |
| `prepare` | `(candidate: Candidate)` |
| `prepared` | `(consent_rotation_id: bytes32, request_digest: bytes32, under_duress: bool)` |
| `commit` | `(consent_rotation_id: bytes32, prepared_envelope_digest: bytes32)` |
| `committed` | `(consent_rotation_id: bytes32, request_digest: bytes32)` |
| `abort` | `(consent_rotation_id: bytes32, previous_set_checked: bool, under_duress: bool)` |
| `abort_unheld` | `(authorization: SignedMessage<MessageWithNonce<bytes32>>, under_duress: bool)` |
| `aborted` | `(consent_rotation_id: bytes32, request_digest: bytes32, under_duress: bool)` |
| `finish` | `(expected_consent_freshness_token: bytes32, next_consent_freshness_token: bytes32, approved_withdrawal_id: bytes32, sar_receipt: CbcCmacEnvelope)` |
| `finished` | `(request_digest: bytes32, next_consent_freshness_token: bytes32)` |

HOLD, PREPARE, COMMIT, ABORT, ABORT_UNHELD, and FINISH flow source to target;
their receipts flow back. Each request digest is EH of the exact request envelope.

Source releases PREPARE only after durable previous-answer acceptance and both
candidate confirmations. Target accepts it only while HELD with the original
rotation ID, valid new set different from its current set, and source signature
against the retained identity key. That signature attests to completed input checks.
Target OR-merges the flag into the otherwise identical candidate and persists it,
prepared state, and exact PREPARED before reply. PREPARED attests to durable
storage of the exact PREPARE's rotation ID and set with the returned merged flag.
Source verifies the paired signer, rotation ID, and EH of its retained PREPARE,
rejecting a false flag if its candidate's flag is true. It keeps the candidate's
ID and set, installs the returned flag, and atomically persists the OR merge,
prepared candidate, and exact receipt. Both prepared candidates are immutable.
No further country answers are accepted after PREPARE; exact accepted-answer
retries recover their cached successors.

COMMIT requires both durable prepares. Source atomically installs the candidate
and records irrevocable COMMIT and exact bytes before sending. Target requires
the current rotation ID, prepared phase, and EH of its exact retained PREPARED.
That receipt binds the PREPARE and merged flag, identifying the immutable
candidate to install. Target atomically installs it, clears consent quarantine,
and stores COMMITTED. Source verifies the paired signer, rotation ID, and EH of
its exact irrevocable COMMIT before clearing its hold. COMMITTED attests to
installation of that prepared candidate. Target remains inactive. Commit retains
the freshness token installed at admission.

ABORT is permitted only before source COMMIT. Source records that decision and
its latest flag before output. Target OR-merges the flag and persists quarantine,
terminal decision, and exact ABORTED before reply. Source persists its OR merge
before resolving. A PREPARED target requires `previous_set_checked=true`.
An unacknowledged HOLD instead uses ABORT_UNHELD with the original ST approval,
independently of classification. No previous answer has run in that phase.
Target accepts it only for an unseen admissible predecessor or the same HELD
attempt, consumes the token if unseen, and returns ABORTED. PREPARED or COMPLETE
cannot accept that variant. Terminal decisions reject conflicts.

## Paused withdrawal and resumption

Checkpoint PSBT, identifiers, approvals and commits, phase and stall reason,
accepted ST results, mystery, counter, next unused Ping sequence, reached
evidence, last-seen block, replay memory, retained fragments, signing nonce-use
history, and exact pending SAR duties. Reserve storage before admission.
Rotation assumes no live MuSig2 exchange.

While held, source produces no new progress, withdrawal ST input, signing output,
or fragment export. It can retransmit emitted messages and consume their exact
SAR receipts. Retire unsent Pings while preserving reserved sequences.
Unconsumed pre-pause Pongs cannot credit later progress. Retire any pending
withdrawal country challenge; its replacement after commit uses the new set,
fresh nonce, and retained withdrawal identity and phase.

Only verified COMMITTED permits in-place resumption, including receipt and replay
updates accumulated during pause. Reapply ordinary freshness and chain-view
gates. Rotation supplies no approvals, mystery, progress credit, or deadline
extension. Abort or uncertainty leaves consent quarantined and withdrawal held.

After COMMITTED, persist a resume gate bound to the current freshness token,
initially without an expected packet. Older SAR duties remain separate. Preserve TxCommit
bytes and emit a fresh Ping at the next unused sequence carrying the flag.
Persist the gate token, exact packet, and expected placeholder before sending.
Recovery and retries reuse that record. Until its exact SAR receipt clears the
gate, no counter credit, new signing output, or fragment export is allowed.

For every valid Ping, WT forwards the placeholder to the setup-bound SAR and
immediately relays
`(approved_withdrawal_id, duress_placeholder_signed_by_sar_encrypted_by_sar_for_boomlet_0)`
through Niso, including after digging ends. Source verifies the bound approved
ID, SAR signer and context, and signature over the exact expected placeholder.
An older receipt cannot clear a newer token's gate. Receipt consumption clears
only the resume gate, never `under_duress`.

After digging termination, WT replaces the source's slot in its retained reached
collection with the latest true Ping and redistributes it for ordinary signing
revalidation. Stale evidence still stalls. A receipt creates no progress or Pong
and cannot reopen digging. Rotation cannot revoke released signing output;
backup activation still needs independent current-state and source-exclusion
evidence.

## Withdrawal end and paired reset

Before withdrawal teardown, retire outstanding ST input and freeze further flag
updates. Emit a fresh final Ping carrying the current flag at the next unused
sequence for either classification. Persist its exact packet and expected
placeholder and consume the matching SAR acknowledgment before reset. WT retains
the delivery record through teardown and accepts this final Ping under its
ordinary checks even after digging termination. Its receipt proves delivery,
not signing or progress authority. Restart recovers the final packet and receipt;
abandonment or failure without acknowledgment preserves the flag and SAR duties.
Closing blocks new withdrawals, rotations, and duress input until delivery and
any paired reset complete. If abandonment precedes an approved withdrawal ID,
carry the flag into the next withdrawal instead.

If rotation ran between withdrawals, this reset belongs to the next withdrawal.
A completed or abandoned rotation alone cannot clear the flag. Unresolved or
quarantined rotation blocks paired reset.

When `paired_reset_pending` is true, source creates FINISH with its current token,
a fresh next token distinct from the current one, the ending approved withdrawal
ID, and the exact final SAR receipt. It records withdrawal end, verified receipt,
and exact FINISH before sending, retaining the flag. Until FINISHED is consumed,
no new withdrawal,
rotation, or duress answer can begin.

Target verifies the source signature against its retained identity key and checks
the fixed pair, current predecessor token, inactive role, and absence of an
unresolved or quarantined rotation.
Using the copied logical peer's channel keys only for verification, it decrypts
the SAR receipt with its stated approved ID, verifies the setup-bound SAR signer
and response domain, and authenticates the enclosed placeholder under that ID.
Plaintext must be zeros or `doxing_key_for_sar`; a true local flag requires the
key-bearing value. The source signature attests that this is the exact final
receipt for the ended withdrawal. No host-supplied receipt can request reset
without that signed statement.

Target atomically clears the flag, installs the next token, and stores exact
FINISHED before reply. Source verifies request digest, paired channel, and next
token, then atomically installs that token, clears the flag and
`paired_reset_pending`, and completes teardown while preserving replay and
rescue obligations.
Both classifications use the same FINISH exchange, writes, and deadlines.
A missing receipt blocks cleanup; RESUME retransmits exact FINISH, and target
returns cached FINISHED without clearing anything again. A conflicting or
superseded reset is rejected.

Where no rotation flag was replicated, `paired_reset_pending=false`; source may
reset locally after withdrawal end and final SAR acknowledgment. This choice
depends on whether rotation occurred, never on classification. After reset, old
rotation receipts and country answers can only recover cached terminal results;
they cannot OR-merge an earlier flag into a later withdrawal. Reset changes no
consent set and cannot cancel SAR activation already recorded.

## Contexts, recovery, and bounds

For each control operation:

```text
domain(op) = "Boomerang/consent_rotation/v1/" + op
context(op) = canonical_encode("consent_rotation_" + op, setup_instance_id)
E = cbc_cmac_encrypt(directional_channel_keys, context(op),
                    sign_message(sender_identity_privkey, domain(op), content))
```

Source messages use `boomlet_0_identity_privkey`; target messages use
`boomletwo_Identity_privkey`. SPEC's `channel_keys` uses their corresponding
public keys, roles `boomlet` and `boomletwo`, direction, and protocol version.
Operation strings are fixed profile constants. Sender attribution relies on
the protected applet roles above.

ST suffixes are `review_challenge`, `review_approval`, `previous_challenge`,
`previous_answer`, `previous_result`, `selection_challenge`, `selection_answer`,
`confirmation_1_challenge`, `confirmation_1_answer`, `confirmation_2_challenge`,
`confirmation_2_answer`, `round_result`, `cancel_challenge`, `cancel_approval`,
`terminal_result`, `ui_status`, and `ui_status_response`. Context is
`canonical_encode("consent_rotation_" + suffix)`. Review and cancellation
approvals are signed under their specified domains; channel authentication
protects other ST payloads.

ST recovery uses a fresh ST-generated query nonce and
`(consent_rotation_id: bytes32)`. Source requires the recorded rotation ID and
returns `(consent_rotation_id: bytes32, result: u8, pending_input: PendingConsentInput)`,
echoing the query nonce, with result 0 pending, 3 complete, or 4 aborted.
Retire and replace only unconsumed challenges, durably supplying the fresh one
inline. Pending cancellation uses `input_pending=true`, input step 5, enrollment
round 0, a fresh cancellation nonce, and identity space as padding. Absent input
has `input_pending=false`, enrollment round and input step 0, zero nonce, and
identity space 1–193; ST never displays padding.

Source retains up to eight accepted ST recovery query digests in acceptance order and one
exact encrypted reply for the last query. Each attempt starts with an empty list
and no reply. Compute each digest as
`sha256(canonical_encode(consent_rotation_st_recovery_request_with_nonce))`
after verifying the ST channel and recorded rotation ID. The last query's duplicate returns that
reply without writes or input replacement. A digest present earlier in the list
is superseded and rejected without reply or state change. A fresh query requires
a free slot; exhaustion rejects it while preserving the last query's exact retry.

For a fresh query, atomically append its digest, replace the cached encrypted
reply, and persist any replacement challenge before sending. Discard the
superseded UI reply. Preserve accepted answers, the flag, and decisions. Restart
recovers the digest list and current reply together. Cached replies are immutable
snapshots; later phase progress cannot regenerate a reply for the same query.
ST retains one outstanding query and retries its exact envelope. It accepts only
an authenticated reply matching that attempt and echoing the query's nonce.
After state loss or abandoning a query, ST uses a fresh nonce to recover current
input or a terminal result.

Rotation phases are 0 HOLD_WAIT, 1 HELD, 2 PREVIOUS_PENDING, 3 ENROLLING,
4 PREPARE_WAIT, 5 PREPARED, 6 COMMIT_WAIT, 7 COMPLETE, 8 ABORT_WAIT, and 9 ABORTED.
Target uses HELD, PREPARED, COMPLETE, and ABORTED; COMPLETE there is committed
inactive. Resume and paired reset gates remain separate durable records.
Invalid input preserves phase and flag. Prepared targets cannot decide from
silence or timeout. Source decisions serialize against accepted ST responses.

Device recovery uses exact retained control envelopes through their ordinary
handlers. RESUME returns the device's pending outbound control or ST envelope;
an undecided prepared target returns its original PREPARED. First delivery in an
expected active phase follows normal validation and atomic persistence. Exact
recorded duplicates return the durable successor below without writes, new
input, or flag merging. If no successor exists yet, keep the hold. Source may
continue its ordinary decision step from durable PREPARED, persisting COMMIT or
ABORT before transmission.

| Received recorded envelope | Retained successor, when available |
| --- | --- |
| HOLD | HELD, or the terminal receipt |
| HELD | Pending PREPARE, ABORT, or ABORT_UNHELD |
| PREPARE | PREPARED, or the terminal receipt |
| PREPARED | Recorded COMMIT or ABORT |
| COMMIT | COMMITTED |
| ABORT or ABORT_UNHELD | ABORTED |
| FINISH | FINISHED |

Replies retain their original request digests. Ordinary pairing, attempt, phase,
and request-digest checks apply; FINISH uses its reset bindings above. Conflicting
content is rejected. Once source records a decision, even a first late HELD or
PREPARED matching its retained request can only retransmit that decision, without
input, candidate changes, or flag merging. Receipt replay and timeout never
choose a decision.
Terminal receipts cannot overwrite a decision, repeat a merge after reset, or
affect a superseding attempt. Superseded envelopes are stale. Source COMPLETE
requires retained COMMITTED.

Retain current control messages, response digests with cached successors, and
last terminal decision and receipt. Before admitting a successor, compact
completed input, candidates, and prepare envelopes that contain an earlier set.
Only the current committed set and an unresolved candidate need retention.
Recovery cannot erase signing, replay, or rescue evidence.

Verify CBC-CMAC before decryption. New envelopes use fresh IVs; retries reuse
stored bytes. Either flag value uses identical bounded comparison, storage,
queues, permitted failures, and trusted fixed response deadlines.
Set `release_at = trusted_received_at + reply_delay[operation]` before parsing.
A missed deadline yields the same failure and no late reply, while retaining any
durable decision. Measured worst-case device work must fit those deadlines.
No observer-accessible status, logs, metrics, or diagnostics reveal classification.

| Bound | Value or requirement |
| --- | --- |
| Enrollment rounds | 3; selection and two confirmations per round |
| Automatic exact-delivery retries | 8 per object; exhaustion stalls and preserves state |
| Fresh ST recovery queries | 8 per attempt |
| ST recovery cache | At most 8 accepted query digests and one exact encrypted reply per attempt |
| Control envelope maximum | 2,048 bytes, including FINISH |
| ST envelope maximum | 1,536 bytes |
| Transport frame | 4,096 bytes between devices, 2,048 for ST |
| Decoded nesting depth | 12, including wrappers |
| Rotation storage reservation | Current and last terminal records, exact control successors, ST query digests and one reply, checkpoint, and paired reset record before admission |

Automatic exact-delivery retry counters and ST query budgets survive restart and
never depend on the flag. RESUME returns stored bytes without resetting budgets.
Exhaustion preserves retained exact replies and decisions. Admitting a successor
retires superseded input and the preceding attempt's ST digests and reply, then
starts an empty bounded ST cache.

Frames are `operation: u8 || envelope_length: uint16_be || envelope_bytes ||
zero_bytes(frame_size - 3 - envelope_length)`. Device control selectors in table
order are 1–9, 12–13; 10–11 are reserved and rejected. ST selectors are 21–37 in
suffix order. The selector determines the authenticated context and exact payload
type. Framing enters no hash or
signature. Reject nonzero padding, excess lengths, and depth before allocation.
Canonical envelope shape must conceal classification even if relay padding is
removed. Profile changes require a new version and authenticated admission.
