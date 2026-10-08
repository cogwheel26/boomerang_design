# Paired consent rotation message contract

The [proposal](Cannon_paired_consent_rotation_proposal.md) uses the following
typed tuples and the [complete sequence](Cannon_paired_consent_rotation_sequence.puml).
These are proposed extensions to SPEC, not adopted wire types. Canonical
encoding, BIP340, directional ECDH key derivation, and CBC-CMAC follow SPEC
Sections 8–9. Tuple items have the exact order and types below. Unknown versions,
operations, counts, enum values, trailing bytes, and alternative encodings fail
before semantic use. Existing wrapper schemas retain their field definitions.

## Pair binding and attempt scope

```text
PairBinding = (
  consent_profile_version: u16,             // exactly 1
  setup_instance_id: bytes32,
  logical_peer: PeerId,
  source_management_pubkey: bytes33,
  target_management_pubkey: bytes33,
  st_identity_pubkey: bytes33,
  lifecycle_generation: u64
)

Scope = (
  pair_binding_digest: bytes32,
  attempt_seq: u64,
  predecessor_epoch: u64,
  base_state_seq: u64
)
```

`pair_binding_digest` is tagged SHA-256 of canonical `PairBinding` under
`Boomerang/consent_rotation/v1/pair_binding`. Provision and retain a normal-key
signature on that tuple under `Boomerang/consent_rotation/v1/pair_binding`.
Both devices and ST retain that certificate and its verification anchors. The
stored certificate, device's own key, logical peer, ST pairing, setup, and
lifecycle generation must agree. Management keys must be independently generated
and distinct from each other and the copied logical peer key, including their
x-only signing representations. Rotation uses the stored pair certificate.

| Value | Security role and checks |
| --- | --- |
| `pair_binding_digest` | Selects the retained setup, physical pair, ST, lifecycle, and profile during review and admission; later messages must match the admitted scope. |
| `attempt_seq` | Protected admission floor rejects old attempts; country input, decisions, and recovery use it to select the same journal. |
| `predecessor_epoch` | Admission checks the current set version; prepare checks its history prefix, and commit installs epoch plus one. |
| `base_state_seq` | Admission checks the protected consent-state version; accepted previous answers and decisions advance it without depending on classification. |
| Review nonce | Source admission requires its outstanding nonce; target verifies the original ST approval in HOLD or ABORT_UNHELD. |

Both devices retain `last_attempt_seq`, initially 0. A new attempt uses
`last_attempt_seq + 1`; its predecessor epoch and base sequence must match both
devices' protected records. The new epoch is `predecessor_epoch + 1`.
`consent_state_seq` has its own protected floor, advanced on accepted previous-set
answers and decisions, so rollback within an attempt cannot erase accepted duress.
After admission, operations match the journal's scope and enforce their phase,
sequence, and request-digest checks. Terminal retries use the recorded scope,
not the updated predecessor fields, and cannot reopen the attempt.

The source privately binds the review nonce to its current withdrawal identity
or absence of one. Starting, replacing, completing, or abandoning a withdrawal
retires the review. On admission, it rechecks eligibility and durably captures the latest
withdrawal state before pausing. Target imports no withdrawal checkpoint.

Exact current-attempt messages recover their recorded result. Once a later
attempt is admitted, older attempts are stale. Retain the current journal and
last resolved decision and receipt. Starting the next attempt requires a terminal
previous journal at both devices and the preceding receipt durably consumed by
the source. A target cannot replace HELD or PREPARED with a newer attempt.

The source admits one pending intent. An intent lost before authorization
acceptance needs fresh trusted review. After authorization acceptance, its
scope and attempt floor are durable before HOLD is released. A conflicting
scope or different approval at the same sequence is rejected. An admitted
attempt retains its original approval. Inactive targets admit only the bound
source's management operations.

## Trusted review and country input

Niso relays device-encrypted envelopes unchanged. ST uses its existing air-gapped
interface and supplies explicit signed approval. Niso handles public review
metadata and ciphertexts; the ceremony requires no mnemonic, passphrase, or
normal private key.

Niso's local commands request device operations; each device verifies the required
authorization and state. Selector 41 BEGIN_REVIEW has empty tuple input and
returns `(scope, review_envelope)`. Selector 42 SUBMIT_REVIEW takes one
review-approval envelope, durably admits the approved attempt, and
returns the encrypted HOLD. Selector 43 is reserved and rejected.
Selector 44 REQUEST_CANCEL has empty tuple input and produces the cancellation
challenge; 45 RESUME has empty tuple input and resumes the recorded attempt
without new authority. Each contextual payload uses its exact canonical type.
BEGIN_REVIEW is allowed only without an unresolved authorized rotation. An active
withdrawal qualifies during DIGGING after commitment and in later phases; a
stalled withdrawal uses its retained phase. The normal commit-collection and SAR
checks and one-time mystery initialization precede DIGGING. Source checks its own
current ceremony state; an early request cannot pause or advance it.
BEGIN_REVIEW creates one volatile pending intent and waits for a free ST input
session; the withdrawal itself can remain active or stalled. Advancing the
attempt floor, quarantining consent, and releasing HOLD require verified ST approval. Public
return values contain no country input or duress state. Requests are rate limited
and malformed input has uniform permitted failures.

The source supplies `MessageWithNonce<Scope>` through its existing Boomlet-to-ST
channel. ST verifies its retained pair certificate and the scope's binding digest
against its authenticated pairing and displays consent replacement, setup,
device identities, and epochs. Explicit user approval
makes ST sign that exact nonce-bound scope under
`Boomerang/consent_rotation/v1/st_review`.
This `SignedMessage<MessageWithNonce<Scope>>` authorizes rotation within the
stored pair; the previous-set answer classifies duress.

SUBMIT_REVIEW verifies the stored normal-key pair certificate, the ST signature
under `Boomerang/consent_rotation/v1/st_review`, and the exact pending scope and
review nonce. It rechecks the predecessor, private withdrawal binding, phase
eligibility, attempt floor, and storage capacity before admission. The source
atomically persists the approval, scope, source withdrawal checkpoint and pause,
advanced attempt floor, quarantine, exact HOLD, and
`duress_latched OR current_check_is_duress` before releasing HOLD. Exact approval
retries return the cached HOLD without another admission, counter advance, or
write. Terminal attempts remain terminal; delayed HOLD or HELD cannot reopen
them. Once a later attempt is admitted, an older approval is stale.

HOLD carries the ST-signed approval. Its scope is `authorization.content.content`.
The target independently verifies its retained certificate under the pair-binding
domain and the approval under `Boomerang/consent_rotation/v1/st_review` against
its retained normal and ST public keys. It requires the approval scope to match
its stored binding and a matching inactive role, predecessor, and attempt floor.
Freshness comes from the review nonce at source and protected attempt floors at both devices, not host
timestamps.

Profile provisioning gives both devices and ST the certificate, setup ID, normal
public key, pair digest, and lifecycle generation alongside their authenticated
device pairing. They retain these anchors; an incoming review cannot install another
binding. The reviewed logical peer and descriptor must identify the user's
intended setup. Device replacement, rebinding, signing, and Boomletwo activation
retain their separate authorization requirements.

```text
Check = (scope: Scope, round: u8, phase: u8, space: DuressCheckSpace)
Answer = (scope: Scope, round: u8, phase: u8, selection: DuressSignalIndex)
UiResult = (scope: Scope, round: u8, result: u8)
UiResume = (present: bool, round: u8, phase: u8, nonce: bytes32, space: DuressCheckSpace)
```

Challenges and answers use `MessageWithNonce<Check>` and
`MessageWithNonce<Answer>`. `space` contains one permutation of integers 1–193.
ST creates the five shuffled display columns and returns five distinct original
indices. It prevents duplicate user selections. Phase values are 1 previous set,
2 new selection, 3 first confirmation, and 4 second confirmation. Round is 0
for the previous set and 1–3 for enrollment. Each phase gets a fresh nonce and
permutation; both endpoints require the exact scope, round, phase, and nonce.

Before releasing a challenge, source persists its nonce, permutation, phase,
and exact encrypted bytes. Each accepted answer is atomically consumed with
its response digest, state changes, and cached result or next challenge.
Restart recovers these records; an unconsumed challenge may instead be durably
retired and replaced with a fresh nonce. Replayed retired nonces cannot satisfy
another phase. Accepted-response retries return the cached successor without
another comparison, write, prompt, or counter increment.

ST also treats `(scope, round, phase, nonce)` as one input session. A duplicate
challenge before answer preserves its display maps and selections. After answer,
it resends the exact cached encrypted answer without prompting again. Conflicting
challenge content at the same nonce is rejected. ST state loss uses UI status
recovery below; it cannot redisplay a captured challenge as a fresh session.

The previous answer always returns `UiResult` 0 CONTINUE. Persist the latch and
`answer_seq = base_state_seq + 1` before that result leaves the device. Compare
all five values even when duress is already latched. Both classifications use
the same write and release path.

Each enrollment round runs selection and both confirmations before reporting
1 RETRY or 2 READY. READY requires five valid distinct country values, no reuse
in committed history, and both confirmations matching. Comparisons use sorted
country values; selection order has no meaning. An invalid history choice still
runs both confirmations. After round 3 failure the source decides ABORT.
Authentication and encoding failures stall the outstanding phase instead of
being treated as country mismatches. Country confirmation failures do not
increment `consent_state_seq` or clear duress.

UI results use `MessageWithNonce<UiResult>` with the answered nonce. The round
result echoes the second-confirmation nonce. Terminal results are 3 COMPLETE
or 4 ABORTED, anchored to the latest outstanding or accepted ST nonce, or the
review nonce when no country prompt ran. ST retains that scope and nonce until
terminal delivery; duplicates cannot repeat visible prompts. ST state loss
requires a fresh authenticated status challenge to source before displaying a
terminal result, not acceptance of an old unsolicited result.
Recovered terminal displays identify the returned attempt and never attach an
older result to a different intent.

User cancellation before commit requires ST to sign a fresh nonce-bound Scope
under `Boomerang/consent_rotation/v1/st_cancel`. Source retires any pending
country challenge before issuing this cancellation challenge. Accepted duress
survives. Repeated REQUEST_CANCEL returns the cached outstanding challenge;
it cannot repeatedly retire input or allocate nonces. Without approval the
ceremony remains held. Acceptance atomically consumes the cancellation nonce
and records cancellation before any decision or reply; exact approval retries
recover that result. No cancellation request can change a durable COMMIT.

## Candidate and control messages

```text
Candidate = (
  scope: Scope,
  new_set: list<u16>,                       // exactly 5, ascending, distinct
  history_count: u16,
  history_slots: list<list<u16>>,           // exactly 32 rows of 5 items
  answer_seq: u64,                         // base_state_seq + 1
  final_state_seq: u64,                    // base_state_seq + 2
  duress_latched: bool
)
```

Active history rows are sorted valid five-country sets, distinct and in epoch
order. Unused rows are exactly five zeros, used only as padding. Committed
`history_count = consent_epoch + 1`; candidate count is predecessor count plus
one. The prefix must match retained history and the final active row must equal
`new_set`. Neither zero padding nor missing history can represent active consent.
The fixed capacity permits initial enrollment and 31 successful rotations.

Define `EH(E) = sha256(canonical_encode(E))` for an encrypted envelope, and
`CD(C) = tagged_sha256("Boomerang/consent_rotation/v1/candidate",
canonical_encode(C))`. CD and all latch-bearing content remain encrypted.

| Operation | Exact signed content tuple |
| --- | --- |
| `hold` | `(authorization: SignedMessage<MessageWithNonce<Scope>>)` |
| `held` | `(scope: Scope, request_digest: bytes32, state_seq: u64, duress_latched: bool)` |
| `prepare` | `(candidate: Candidate)` |
| `prepared` | `(scope: Scope, request_digest: bytes32, candidate: Candidate)` |
| `commit` | `(scope: Scope, prepared_envelope_digest: bytes32, candidate_digest: bytes32, final_state_seq: u64)` |
| `committed` | `(scope: Scope, request_digest: bytes32, candidate_digest: bytes32, final_state_seq: u64, duress_latched: bool)` |
| `abort` | `(scope: Scope, previous_checked: bool, final_state_seq: u64, duress_latched: bool)` |
| `abort_unheld` | `(authorization: SignedMessage<MessageWithNonce<Scope>>, final_state_seq: u64, duress_latched: bool)` |
| `aborted` | `(scope: Scope, request_digest: bytes32, final_state_seq: u64, duress_latched: bool)` |
| `status` | `(scope: Scope, query_nonce: bytes32)` |
| `status_response` | `(scope: Scope, request_digest: bytes32, query_nonce: bytes32, journal_phase: u8, state_seq: u64, evidence_kind: u8, evidence: bytes)` |

HOLD is source to target; HELD is target to source. PREPARE and COMMIT flow
source to target with corresponding target receipts. ABORT follows the same
direction. STATUS works in either direction. Each `request_digest` is EH of
the exact request envelope. HELD's state sequence must equal the scope's base;
source durably OR-merges its returned latch before asking for the previous set.

Target accepts PREPARE only while HELD, with matching scope and completed
source answer sequence. It verifies candidate history and computes an otherwise
identical candidate whose latch is local OR received. Before PREPARED release,
persist the merged latch, candidate, mirrored answer sequence, and exact receipt.
Source verifies EH and every candidate field, permitting only a false-to-true
latch merge, then durably records the same prepared candidate.

COMMIT requires both durable prepares. Source installs the candidate and records
the decision and exact COMMIT bytes atomically before output. Target requires
the digest of its exact PREPARED envelope, matching CD and final sequence;
it installs the prepared candidate and exact COMMITTED receipt atomically.
Source remains withdrawal-held until the matching receipt is consumed. Target
resolves its rotation hold but retains its inactive lifecycle gate. Installing
the candidate sets `consent_epoch = scope.predecessor_epoch + 1` on both devices.

ABORT is permitted only before source COMMIT. Its final sequence is base plus
1 when no previous response was accepted, otherwise base plus 2. Source records
that decision and its latest latch before output. Target OR-merges the latch and
persists the sequence, quarantine, terminal decision, and receipt before reply.
Source persists its OR merge of ABORTED before resolving. With HELD unacknowledged,
source instead sends ABORT_UNHELD with the original ST approval,
independent of duress. No previous answer can have been accepted in this phase;
its final sequence is base plus 1. Target accepts it only when unseen or HELD,
after the same retained-certificate, ST approval, and scope checks as HOLD. It records
the attempt floor and quarantine and returns ABORTED. It cannot accept
that variant after PREPARED or COMPLETE.
Terminal decisions reject conflicts and preserve exact receipt retries.
At PREPARED, a regular ABORT must assert `previous_checked=true`; its final
sequence must equal the prepared final sequence. A reserved or prepared sequence
is never itself evidence that COMMIT occurred.

## Paused withdrawal and resumption

The source checkpoint preserves PSBT, transaction and withdrawal identifiers,
approval and commit collections, phase and stall reason, accepted ST results,
mystery, counter, next unused Ping sequence, last-seen block, reached evidence,
replay floors, retained fragments, signing nonce-use history, and pending exact SAR envelopes.
Reserve capacity for this record alongside both journals before admission.
Rotation assumes no live MuSig2 exchange. Pause and recovery cannot discard an
accepted duress result, revive a consumed nonce, or abandon and restart the withdrawal.

While held, source performs no new withdrawal progress, ST check, signing output,
or fragment export. It can retransmit exact already emitted protocol messages
and validate their exact SAR receipts; these duties survive pause and abort.
Retire queued Pings that have not been emitted, preserving their reserved
sequences. Their replacements carry current duress at the next unused sequence.
Unconsumed pre-pause Pongs cannot later credit progress. Retire any pending
withdrawal country challenge at admission and retain its nonce in replay memory;
after consent commit its replacement uses the committed set, fresh space and
nonce, and the retained withdrawal phase and identity.

Only a verified COMMITTED receipt permits source resumption. Resume the
checkpoint in place with monotonic receipt and replay updates accumulated during
pause; never restore an older duress or signing record. Reapply normal freshness
and chain-view gates. Expired inputs stall or follow existing failure handling;
rotation supplies no new approvals, mystery, progress credit, or extended deadline.
Other stall reasons still require their ordinary valid retry or recovery input.
Abort or unresolved rotation leaves consent quarantined and the withdrawal held.

Set a durable withdrawal resume gate bound to the new consent epoch after
COMMITTED, initially without an expected packet. Keep older SAR duties separately;
their receipts cannot clear this gate. Preserve the initial TxCommit bytes and emit a fresh Ping at the next
unused sequence with current effective duress. Mystery and counter remain
unchanged. Persist the gate epoch, exact new packet, and expected placeholder
before releasing it. Recovery and retries reuse that record.

WT forwards every placeholder to the setup-bound SAR. For every valid Ping, WT
immediately relays `(approved_withdrawal_id, duress_placeholder_signed_by_sar_encrypted_by_sar_for_boomlet_0)`
through Niso, including after distributing reached evidence. Niso forwards the
same fields unchanged. WT retains all normal Ping checks; exact duplicates
return cached receipts. After digging termination, WT updates the source's slot
in its retained reached collection with the latest true Ping and redistributes
that collection for ordinary signing revalidation. Stale peer evidence still
stalls. A receipt alone neither creates a Pong nor reopens digging. Source verifies its bound
approved ID, SAR signer and context, and signature over the exact newly emitted
placeholder, then durably consumes the receipt and clears the gate. Old receipts
satisfy only their original duties. Exact packet and receipt retries are cached.
Until this gate clears, no counter credit, new signing output, or fragment export
is permitted; the ordinary approval, digging and signing gates remain mandatory.

A rotation after signing output cannot revoke that output. Backup activation
still requires current signing, replay, withdrawal, and rescue evidence;
the consent receipt provides no such authority.

## Contexts, signatures, and release

For each control operation in the table:

```text
domain(op) = "Boomerang/consent_rotation/v1/" + op
context(op) = canonical_encode("consent_rotation_" + op, setup_instance_id)
E = cbc_cmac_encrypt(directional_management_keys, context(op),
                    sign_message(sender_management_key, domain(op), content))
```

Operation strings are fixed profile constants, never host-provided labels.
Management keys use entity roles `boomlet` and `boomletwo`, with certified
physical keys, direction, and PROTOCOL_VERSION in the KDF. Existing logical
Boomlet-to-ST keys encrypt review and country messages; the inactive target
cannot exercise the copied logical identity to initiate those flows.

ST operation suffixes are `review_challenge`, `review_approval`,
`previous_challenge`, `previous_answer`, `previous_result`,
`selection_challenge`, `selection_answer`, `confirmation_1_challenge`,
`confirmation_1_answer`, `confirmation_2_challenge`, `confirmation_2_answer`,
`round_result`, `cancel_challenge`, `cancel_approval`, `terminal_result`,
`ui_status`, and `ui_status_response`. Their contexts are
`canonical_encode("consent_rotation_" + suffix)` without setup ID, as nonce-bound
local flows. Review and cancel approvals are ST-signed under their specified
domains; other ST payloads are authenticated by the channel. The nonce-bound
scope inside each payload binds setup and attempt. UI status uses a fresh
ST-generated nonce and `(pair_binding_digest: bytes32)`
request; source returns
`(scope: Scope, result: u8, resume: UiResume)`, echoing that nonce, with result 0
pending, 3 complete, or 4 aborted from the durable journal. A pending unconsumed
country challenge is retired and replaced with a fresh nonce and permutation;
the fresh challenge is persisted and supplied inline as `resume`. The ST uses
only this nonce-bound resumption after restart. Accepted answers and decisions
remain intact. A pending cancellation uses `present=true`, phase 5, round 0,
a fresh cancellation nonce, and the identity space as padding. ST confirms
cancellation and signs `MessageWithNonce<Scope>` with that nonce. Phase 5 is
valid only in UiResume. Without a pending challenge, `present=false`, round and
phase are 0, nonce is zero, and space is the identity permutation 1–193; ST never
displays those padding values. Exact duplicate UI queries recover their cached
reply without retiring another challenge. This exchange changes no decision.

CBC-CMAC verification precedes decryption. New envelopes have fresh IVs;
exact retries retransmit stored bytes. Valid operations and either latch value
perform identical bounded writes and response scheduling. Set
`release_at = trusted_received_at + reply_delay[operation]` before parsing.
Release valid replies exactly at that deadline; a missed deadline has the same
failure at the deadline and no late reply. A durable decision is retained even
when its reply misses the deadline. Reply timers and release gates must be
trusted device functions, not host promises. Actual delay values require
worst-case device measurements before deployment.

## Recovery and bounds

Journal phases are 0 HOLD_WAIT, 1 HELD, 2 PREVIOUS_PENDING, 3 ENROLLING,
4 PREPARE_WAIT, 5 PREPARED, 6 COMMIT_WAIT, 7 COMPLETE, 8 ABORT_WAIT, and 9 ABORTED.
Target uses HELD, PREPARED, COMPLETE, and ABORTED; COMPLETE there means committed
inactive. A source COMPLETE journal can still have a withdrawal awaiting its
resume SAR receipt; recovery preserves that separate gate and exact packet.
A request with no admitted journal fails uniformly; preauthorization ST state
loss requires fresh review.
Invalid inputs preserve the phase and latch. A prepared target cannot decide
from silence or timeout. Source decision transitions serialize against all
accepted ST responses and conflicting operations.
Late replies cannot advance a terminal journal or another attempt. An old
valid HELD received after ABORT cannot issue a previous-set prompt.

STATUS uses a fresh query nonce. Replies bind that nonce and EH of the request;
stale replies cannot overwrite journal phase. Evidence kind is 0 none, 1 COMMIT,
2 ABORT, 3 COMMITTED, 4 ABORTED, or 5 ABORT_UNHELD. Evidence is the canonical bytes of that
original encrypted message, or empty bytes for kind 0. Recover it through its
ordinary decision or receipt handler, including that handler's durable latch
merge. STATUS itself changes no consent state or authority. For ABORT without
HOLD, recover its authorization-bearing variant. Never reduce a protected
sequence. Source COMPLETE requires retained COMMITTED evidence.

Each direction admits at most eight distinct STATUS query nonces per attempt;
source admits eight UI status nonces. The requester reserves its slot and exact
request before release. Reserve their reply caches with the journal. Persist first acceptance and exact reply once; duplicate
queries use that cache without another write or challenge replacement. Every
fresh UI query consumes its slot even without a pending challenge. Exhaustion
stalls fresh queries while retaining exact retries, decisions, and duress.
These budgets survive restart and never depend on classification.

Each endpoint retains exact current control messages, last terminal decision
and receipt, and accepted ST response digests with cached successors. At most
one country challenge is outstanding. Compaction occurs only after terminal
evidence is durable and superseded messages cannot authorize work below the
attempt floor. Recovery cannot erase queued rescue or signing evidence.

| Bound | Value or requirement |
| --- | --- |
| Committed history slots | 32, padded on every transfer |
| Enrollment rounds | 3; selection and two confirmations per round |
| Automatic exact-delivery retries | 8 per object; exhaustion stalls and preserves state |
| Fresh status queries | 8 per direction per attempt; 8 UI queries per attempt |
| Control envelope maximum | 2,048 bytes; authorization-bearing ABORT uses the same bound |
| Status evidence maximum | 2,048 bytes, one original envelope |
| Status envelope maximum | 3,072 bytes |
| ST envelope maximum | 1,536 bytes |
| Transport frame | 4,096 bytes for management, 2,048 for ST; operation selector, envelope length, and zero padding |
| Decoded nesting depth | 12, including wrappers |
| Counter admission | Attempt floor below u64 maximum, base sequence at most maximum minus 2, and free history slot |
| Journal reservation | Space for current and last terminal records, cached responses, and atomic replacement before HOLD acceptance |

The frame is `operation: u8 || envelope_length: uint16_be || envelope_bytes ||
zero_bytes(frame_size - 3 - envelope_length)`. Management selectors, in table
order, are 1 HOLD, 2 HELD, 3 PREPARE, 4 PREPARED, 5 COMMIT, 6 COMMITTED,
7 ABORT, 8 ABORT_UNHELD, 9 ABORTED, 10 STATUS, and 11 STATUS_RESPONSE. ST
selectors are 21–37 in suffix order. The selector determines the expected
authenticated context and exact payload type; tampering cannot change them.
Transport framing does not enter hashes or signatures. Parse exactly the
declared envelope bytes and reject nonzero padding or excess length. Even if
a relay removes transport padding, the canonical envelope shape must reveal
no classification. Check bounds before allocation, including decrypted payloads
and status evidence. Explicit retry resumption reuses the same object and never
resets replay floors. A different capacity or retry profile needs a new consent
profile version and authenticated admission.
