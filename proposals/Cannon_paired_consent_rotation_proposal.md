# Paired consent rotation proposal

[Complete sequence](Cannon_paired_consent_rotation_sequence.puml).
Decisions are recorded in [ADR 0009](../adr/0009-paired-consent-rotation.md) and
[ADR 0010](../adr/0010-niso-relayed-consent-rotation.md).

These SPEC extensions remain proposed and unadopted. Encoding, signatures,
directional channels, and CBC-CMAC follow SPEC Sections 8–9.

## Behavior

Boomlet and its designated inactive Boomletwo replace their unordered
five-country `duress_consent_set`. The descriptor, logical peer, ST input method,
and WT and SAR registrations remain intact. New attempts begin only in `IDLE`
or `DIGGING`; a stalled withdrawal uses its retained phase. DIGGING includes
waiting for other peers after reaching the local mystery threshold.

The user enters the current set on ST to approve rotation, chooses the new set,
and confirms the new set once. Boomlet sends Boomletwo one authenticated message
containing ST approval, the chosen set, and the duress flag. Boomletwo saves the
set and flag before confirming receipt. Boomlet requires that receipt before
resuming consent or reporting completion.

Every successful replacement MUST include the current-set check through trusted
ST. A valid wrong answer MUST durably latch duress before any reply and continue
through the same selection, confirmation, and delivery flow as a correct answer:

```text
under_duress := under_duress OR answer_is_wrong
user_is_in_duress := under_duress
```

Correct answers, cancellation, confirmation, retries, restart, and further
rotation cannot clear the flag. Wrong ordinary withdrawal answers can also set
it. Subsequent commitments and Pings carry the key-bearing SAR placeholder while
it is true. Idle duress carries into the next withdrawal. A valid mistaken answer
can cause false duress.

Confirmation must match the selected set and that set must differ from the
current one. Cancellation, a valid confirmation mismatch, or selecting the
current set leaves the set unchanged. These outcomes still send the current set
and latched flag and require the same receipt. After receipt both devices agree
and consent may resume, subject to the withdrawal's SAR resumption gate.

Boomlet installs the chosen set when saving its outgoing message; Boomletwo
installs it before replying. Erase the old set at installation. Keep no past sets
or rotation count.

## State and pairing

| State | Meaning |
| --- | --- |
| `duress_consent_set` | Current set; one `new_consent_set` during input. |
| `under_duress` | Durable Boolean, initially false. |
| `consent_token` | Shared 32-byte predecessor value that rejects replayed approvals. |
| `rotation_state` | One attempt: ST approval, current stage and prompt, latest answer digest and exact successors, and exact device and terminal messages. |

Boomlet stages are `selection`, `confirmation`, `waiting_receipt`,
and `complete`. Boomletwo retains its last accepted message and receipt.
An incomplete source attempt pauses consent and any existing withdrawal.
A completed attempt remains until the next admission or paired reset.

All accepted state changes and exact outbound messages MUST be atomic and
rollback-resistant before output. Reserve bounded space for one attempt, its
recovery cache, and a paired reset. Keep reset receipts separately for retries.
Derive `rotation_id` from the retained ST approval's nonce. Existing signing,
replay, and rescue evidence remains in the withdrawal record.

Use the pair established by setup's normal-key-authorized backup request,
authenticated state transfer, and signed `BackupDone`. Boomlet retains the
backup public key; Boomletwo retains the setup, source, and ST identities.
Require distinct source and backup keys, including x-only representations.
Rotation cannot change those identities.

Boomletwo signs replies with its original identity key. Its inactive applet
confines the copied source key to SAR verification; it cannot originate source,
ST, or withdrawal messages or expose arbitrary signing or encryption with that
key. Roles and restrictions survive restart. The inactive backup only OR-merges
Boomlet's flag, which Boomlet retains until reset.

## Current-set query and approval

Provision the same random `consent_token` on both devices. Boomlet creates
`consent_rotation_request_with_nonce`, a `MessageWithNonce<bytes32>` containing
that token and a fresh nonce distinct from it, and one fresh permutation of 1–193.
It sends both in the initial encrypted query:

```text
ConsentRotationChallenge = (
  request: MessageWithNonce<bytes32>,
  duress_check_space: DuressCheckSpace
)
ConsentRotationAnswer = (
  approval: SignedMessage<MessageWithNonce<bytes32>>,
  duress_signal_index: DuressSignalIndex
)
```

ST authenticates Boomlet and displays “Change consent set. Enter current set to
approve.” Submitting the five choices approves rotation. ST signs the request
under `Boomerang/consent_rotation/v1/st_review` and encrypts approval and indices
together. The approval's nonce binds that response and is `rotation_id`; retain
it and the exact response before output. Boomletwo receives only approval, chosen
set, and flag. No mnemonic, passphrase, or normal private key is needed.

| Local selector | Command and input | Output |
| --- | --- | --- |
| 41 | BEGIN_ROTATION() | Encrypted `ConsentRotationChallenge`. |
| 42 | SUBMIT_CURRENT_SET(first answer envelope) | New-set prompt or retained next message. |
| 45 | RESUME() | Retained next message; Boomletwo returns its current receipt. |

Selectors 43–44 are reserved; local commands supply no authority.
BEGIN_ROTATION requires an active source in IDLE or DIGGING, an available ST
session, and no pending attempt, reset, or teardown. Retain one volatile query,
exact envelope, and withdrawal binding; repeats return it. Withdrawal start,
replacement, end, abandonment, or leaving DIGGING retires it. Loss before
admission requires a fresh query and nonce.

SUBMIT_CURRENT_SET rechecks those conditions, the ST signature, current
predecessor, exact outstanding request, withdrawal binding, and five valid
distinct indices. Resolve them using the retained permutation and compare all
five countries. Atomically save approval, OR-latched duress, consumed response
digest, exact selection prompt, and withdrawal pause before replying. Correct
and valid wrong answers both authorize rotation. Invalid responses admit nothing.
The predecessor token remains unchanged during input.

A retry matching the latest accepted digest returns the exact successor without
reclassification. Earlier responses are stale; conflicting responses cannot
replace an attempt. New admission requires any preceding attempt to be complete
and no pending reset. Pairing or setup changes refresh the token and retire queries.

## New set and confirmation

Selection and confirmation use setup's `MessageWithNonce<DuressCheckSpace>`
prompts and `MessageWithNonce<DuressSignalIndex>` answers, with `rotation_id` as
nonce. Use one immutable prompt and fresh permutation per phase, and setup's
five shuffled columns throughout. ST checks approved nonce and expected phase;
Boomlet checks outstanding phase, nonce, and five valid distinct indices.
Selection and confirmation never classify duress.

Consume each answer with its effects and exact successor; consume confirmation
with the installed set and outgoing device message. Retain only the latest
answer digest and successors. ST retains one display mapping and exact answer.
Duplicate prompts preserve that mapping or return the cached answer; conflicting
content fails. Recovery preserves the current permutation.

Cancellation uses `MessageWithNonce<u8>{content: 0, nonce: rotation_id}` under
`cancel`, authenticated by ST's channel. Verify zero content and a matching
outstanding query or input stage; serialize against the first response, later
answers, and final message creation. Before admission, retire only the volatile
query. After admission, send the unchanged set and latched flag. A saved outgoing
device message is irrevocable; invalid messages preserve pending input.

Save terminal `MessageWithNonce<u8>{content: 3 CHANGED or 4 UNCHANGED,
nonce: rotation_id}` with the outgoing device message and release it after receipt.
ST checks approved nonce and terminal context. Lost query state before admission
requires a fresh first query. ST state loss after admission requires authenticated
status before input or completion.

## Set delivery and receipt

```text
ConsentSetChange = (
  approval: SignedMessage<MessageWithNonce<bytes32>>,
  duress_consent_set: list<u16>,
  under_duress: bool
)
ConsentReset = (
  next_consent_token: bytes32,
  approved_withdrawal_id: bytes32,
  sar_receipt: CbcCmacEnvelope
)
```

A set is exactly five ascending, distinct integers in 1–193. The approval is
signed by ST; its content is the predecessor token and its nonce identifies the
attempt. The source signature attests to accepted input and the chosen outcome.

| Selector | Operation | Exact signed content |
| --- | --- | --- |
| 5 | `consent_set` | `ConsentSetChange`, including ST-signed approval. |
| 6 | `consent_set_received` | SHA-256 of the exact consent-set envelope's canonical encoding. |
| 12 | `reset` | `MessageWithNonce<ConsentReset>` with nonce `consent_token`. |
| 13 | `reset_ack` | SHA-256 of the exact RESET envelope's canonical encoding. |

Requests flow Boomlet to Boomletwo; receipts flow back. Identity signatures bind
the stated operation and protocol version. Both endpoints and their roles are
bound by the paired directional channel; a receipt acknowledges the whole request,
including its approval, set, and flag.

Boomlet atomically installs the chosen set, advances `consent_token` to
`rotation_id`, and saves the exact encrypted message, prepared ST terminal
message, flag, and `waiting_receipt`. Erase prompts, candidate, and predecessor
set; retain the latest answer digest for retries. Both outcomes use this sequence.

Boomletwo verifies both signatures, the fixed pair, inactive role, valid set,
available storage, and no pending reset. Require the approval's predecessor to
equal its current `consent_token` and its nonce to differ from that token.
Atomically install the set, OR-merge the flag, consume the predecessor by adopting
the approval's nonce as `consent_token`, and save the exact request and receipt
before output. Erase the predecessor set and remain inactive.

Boomlet accepts a receipt only while `waiting_receipt`, from its paired backup,
with the exact recorded envelope digest. Atomically retain it, enter `complete`,
and create any paused withdrawal's SAR resumption gate.

## Withdrawal and reset

During DIGGING preserve the withdrawal's identifiers, approvals, phase, mystery,
progress, signing history, replay state, and SAR duties. While paused, produce no
new progress, withdrawal ST input, signing output, or fragment export. Process
exact emitted messages and their SAR receipts. Retire unsent Pings without
reusing reserved sequences, pending withdrawal input, and unconsumed Pong progress.

After receipt, send a fresh next-sequence Ping carrying `under_duress`, retaining
TxCommit. Persist a resumption gate bound to `consent_token`, that exact packet,
and expected placeholder before output. Only its exact verified SAR receipt
clears the gate. Preserve older duties and apply ordinary freshness and chain-view
checks. Require fresh country input using the installed set. Keep local DIGGING
until this receipt, even if WT finishes meanwhile; rotation supplies no progress
credit or deadline extension.

WT forwards each valid Ping's placeholder to the setup-bound SAR and relays
`(approved_withdrawal_id,
duress_placeholder_signed_by_sar_encrypted_by_sar_for_boomlet_0)` through Niso,
including after digging. Verify the approved ID, SAR signer, context, and exact
placeholder. After digging, WT replaces the source's reached evidence with its
latest true Ping and redistributes it for signing revalidation. Receipts create
no Pong, progress, or reopening of digging.

At withdrawal end freeze duress input and send a fresh final Ping for either
flag value. Persist the packet and expected placeholder; require its exact SAR
receipt before clearing the flag. WT retains delivery through teardown.
Block new withdrawals and rotations until delivery and reset finish.
Abandonment before an approved withdrawal ID carries duress into the next withdrawal.

If an attempt record exists, require `complete` and perform paired RESET.
Boomlet records withdrawal end, verified final SAR receipt, and exact RESET,
retaining its flag. Boomletwo verifies the source signature, current-token nonce,
distinct next token, inactive role, and a saved consent-set receipt. Using the
restricted copied-source keys, verify the receipt's approved ID, SAR signer,
context, and placeholder. Its plaintext must be zeros or `doxing_key_for_sar`;
a true local flag requires the key-bearing value. The source signature attests
to this exact final receipt for the ended withdrawal.

Boomletwo atomically clears its flag and accepted consent-set record, installs
the next token, and records exact RESET_ACK before output. Boomlet verifies the
exact pending RESET digest, then atomically clears its flag and attempt, installs
the next token from its own recorded RESET, and finishes teardown. Keep the reset
receipt for read-only retries and preserve signing, replay, and rescue evidence.
With no attempt record, clear locally after final SAR delivery.
Both flag values follow the same reset path. Rotation alone never clears duress.

## Recovery and activation

RESUME returns retained bytes. Authenticate messages, then recognize exact
recorded duplicates before fresh-state checks. An exact consent-set message
returns its cached receipt without reinstalling or merging flags. An exact
RESET returns cached RESET_ACK. Conflicting and superseded messages fail.
Old approvals, answers, device messages, and receipts cannot change another
attempt or a flag after reset.

| Interruption | Recovery |
| --- | --- |
| Before admission | A lost initial query requires a fresh nonce and current-set answer. |
| After admission, during input | Current set and accepted duress remain; resume the pending prompt or cancel through ST. |
| After source installs, before backup receives | Source has the chosen set, backup its predecessor; source stays paused. Retry the exact consent-set message. |
| After backup saves, before source receives confirmation | Both have the chosen set; source stays paused. Retry the message to recover its cached receipt. |
| During reset | Retry exact RESET; cached RESET_ACK cannot clear a later flag. |

Niso stores no authoritative state. Restart recovers atomic records and wrong-answer
duress. Timeout, invalid messages, or unavailable storage preserve the recorded
stage. Permanent loss or rollback blocks uncertain authority.

Boomletwo remains inactive throughout rotation. Activation requires independently
verified source exclusion and current consent, duress, signing, replay, and rescue
state. Boomlet cannot release activation or retirement evidence while an attempt
or SAR duty is unresolved. An old snapshot or consent-set receipt cannot prove
that no later local duress or change exists. If current source state cannot be
recovered, activation stays blocked, including after a crash during country input.
This requirement precedes use of this draft; SPEC Section 18.5 leaves activation open.

For ST recovery, ST sends `MessageWithNonce<bytes32>` containing its approved
`rotation_id` and a fresh ST status nonce under `ui_status`. Boomlet verifies the
ID and returns `MessageWithNonce<RotationStatus>` under `ui_status_response`,
echoing the status nonce:

```text
RotationStatus = (status: u8, space: DuressCheckSpace)
```

Status is 0 WAITING, 2 SELECTION, 3 CONFIRMATION, 4 CHANGED, or 5 UNCHANGED;
1 is reserved. Input statuses carry the current permutation; others use the
identity permutation as padding, which ST never displays. Input always uses
the approved `rotation_id` as its nonce. Status requires a matching admitted
attempt and follows the recorded stage and verified receipt; it never replaces
a prompt or resumes consent. No matching attempt requires a fresh BEGIN_ROTATION,
which still rejects any unresolved attempt. Silence cannot prove non-admission.

Keep one ST status nonce, its exact encrypted reply, and a bounded request count.
The same nonce returns its snapshot. Another nonce snapshots current state and
atomically replaces the cache before output. ST retains one outstanding request,
retries its envelope, and accepts only its matching nonce. State loss requires
a fresh request. Older replayed requests can spend the budget but cannot change
input, flags, or decisions.

## Wire and security rules

Device signatures use `Boomerang/consent_rotation/v1/` plus the operation;
encryption uses `canonical_encode("consent_rotation_" + operation, setup_instance_id)`.
ST encryption uses `canonical_encode("consent_rotation_" + suffix)`.
The approval signature uses its stated domain. The combined initial query and
answer use dedicated `previous_challenge` and `previous_answer` contexts; ordinary
withdrawal answers cannot authorize rotation. Other ST messages use channel
authentication. ST selectors are 23 `previous_challenge`, 24 `previous_answer`,
26 `selection_challenge`, 27 `selection_answer`, 28 `confirmation_challenge`,
29 `confirmation_answer`,
34 `cancel`, 35 `terminal_result`, 36 `ui_status`, and 37 `ui_status_response`.
ST selectors 21–22, 25, and 30–33 are reserved. Device selectors 1–4 and 7–11
are reserved.

| Bound | Requirement |
| --- | --- |
| Input | Current set, new set, one confirmation; one prompt per phase and approved nonce. |
| Automatic retries | Eight per object; preserve state on exhaustion. |
| New ST status nonces | Eight per attempt; retain current reply on exhaustion. |
| Envelopes | At most 2,048 bytes for devices, 1,536 for ST; nesting depth at most 12. |
| Frames | Fixed 4,096 bytes between devices and 2,048 for ST. |

Retry and status counts survive restart; RESUME preserves them. Framing is
`operation: u8 || envelope_length: uint16_be || envelope_bytes || zero_padding`,
excluded from signatures and digests. Enforce exact types, canonical encoding,
lengths, depth, and zero padding before allocation or semantic use. Reject unknown
versions, selectors, and enum values. Fresh messages use fresh IVs; exact retries
reuse stored bytes. Reusing the approved nonce across phases is permitted only
with their distinct fixed contexts and one immutable prompt per phase.

ST approval permits rotation within the fixed pair. Control of the trusted
devices and ST can permit unauthorized maintenance or forced duress. Knowledge
of the correct set can avoid that check's signal. Replacement, rebinding, signing,
and activation retain separate requirements. Rotation cannot revoke released
signing output.

Correct and wrong previous answers and both flag values MUST produce identical
prompts, message counts, lengths, routing, retries, comparison work, durable
writes, queues, trusted fixed deadlines, and permitted failures. Keep sets,
flags, signatures, and receipts encrypted; their canonical shapes must conceal
the flag even if relay padding is stripped. Fix each operation's release time on
arrival before parsing; missed deadlines give the same failure without a late
reply. Keep classification out of status, logs, metrics, and diagnostics,
including recovery and reset, and preserve SPEC Sections 16.3–16.6.
