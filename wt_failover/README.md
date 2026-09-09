# WT failover

A setup authorizes an ordered roster of one to five Watchtowers. All five peers
can replace the active Watchtower with another roster member through a reviewed,
signed decision. The replacement prepares its service before activation, and
each Boomlet preserves its withdrawal security state throughout the change.

`WT_FAILOVER_V1` requires a fresh setup and the complete
[wire](wire_contract.md) and [resource](resource_limits.md) profiles. The base
single-WT format cannot enable it. Adoption also requires full protocol
verification, interoperable cryptographic vectors, and hardware measurements.

## 1. Participants and security boundary

| Participant | Responsibility |
| --- | --- |
| User | Reviews service identities and transactions on a trusted display |
| Boomlet | Secure element holding a peer's identity key, signing share, private withdrawal state, and durable protocol journal |
| Secure Terminal, ST | Trusted display and input device; signs the user's nonce-bound review |
| Niso | Online host that handles networking, transaction data, and local chain observations; its claims cannot authorize Boomlet state changes |
| Iso | Offline device holding the user's normal signing key and participating in local MuSig2 signing with Boomlet |
| Watchtower, WT | Coordinates five peers, checks public evidence, routes placeholders, collects signatures, and broadcasts the approved transaction |
| Search and Rescue service, SAR | Holds encrypted rescue data and processes a peer's encrypted duress placeholders |
| Boomletwo | Designated offline backup; encrypted Ping checkpoints are recovery evidence, subject to unresolved activation safeguards |

There are exactly five peers, each with a Boomlet, ST, Niso, and setup-bound SAR.
The WT roster has one to five entries; a one-entry roster offers no failover.

Every activation requires all five Boomlets. Safety assumes the same logical
peer remains honest, uncloned, and non-rollbackable throughout the relevant
history, including device rollovers. Other peers, Nisos, and WTs may collude,
lie, or alter, replay, delay, and suppress traffic. Each Boomlet enforces its own
authorization and progress rules.

Recorded DIGGING state proves no real chain progress without an authenticated
chain observation available to the honest Boomlet. The inherited chain policy
does not provide one, so the delay guarantee remains blocked under colluding
Niso and WT observations. See [security verification](security_verification.md).

Completion requires all five peers. Candidate preparation may also require the
reviewed WT, payment, user interaction, safe chain observations, and a bound SAR.
A partly voted decision can recover from retained peer evidence without the
candidate or SAR.

## 2. Setup and withdrawal context

### 2.1 Setup agreement

Each peer signs a setup record containing its identity and authenticated peer
contact information. The ordered records, protocol version, ordered WT roster,
and fallback milestone blocks determine `setup_instance_id`. All peers agree on
the same parameter fingerprint and Bitcoin spending descriptor.

Setup progresses through four checkpoints:

| Checkpoint | Required evidence |
| --- | --- |
| `PARAMETERS_AGREED` | Five matching signed parameter fingerprints |
| `WT_READY` | Local WT registration receipt and five matching checkpoint signatures |
| `SAR_READY` | Local SAR finalization evidence and five matching checkpoint signatures |
| `BACKUP_READY` | Base authorized backup and Iso checks, local `BackupDone`, and five matching checkpoint signatures |

Each checkpoint binds the setup ID, phase label, and previous checkpoint. Local
receipts are prerequisites for signing it; peer-specific receipts are separate
from the checkpoint hash. A lone checkpoint signature is pending evidence until
the complete matching collection is verified.

### 2.2 Transaction authorization

A withdrawal begins with a PSBT reviewed by each user on ST. The initiator
generates a fresh approval nonce, and the participants derive:

```text
withdrawal_id = tagged_sha256(
  "Boomerang/withdrawal_id",
  canonical_encode(setup_instance_id, tx_id,
                   initiator_identity_pubkey, initiator_approval_nonce)
)

approved_withdrawal_id = tagged_sha256(
  "Boomerang/approved_withdrawal_id",
  canonical_encode(withdrawal_id, ordered_five_signed_tx_approvals)
)
```

All five approvals name the same withdrawal and follow setup peer order. Each
non-initiator attests to the complete set and the exact WT approval it verified.

The initiator signs a `TxCommit` carrying the approved ID, then pads and signs it
with an encrypted duress placeholder. WT routes that placeholder and acknowledges
the commit only after verifying all four attestations. Non-initiators begin their
initial duress challenge and create commits only after verifying this
acknowledgment. Every Boomlet verifies all five commits and its own exact SAR
acknowledgment before DIGGING.

### 2.3 Duress and DIGGING

Every commit and Ping carries a placeholder encrypting safe plaintext or a rescue
activation key for the peer's fixed SAR. SAR returns an encrypted signature over
the exact placeholder without exposing its classification. Safe and duress paths
use the same acknowledgment delay, durable record, and retry behavior. Exact
replay is idempotent under the approved ID, Boomlet identity, and IV; committed
rescue activation is irreversible.

On first DIGGING entry, Boomlet durably initializes a private random threshold
`mystery`, zero counter, height, and Ping sequence. It signs each Ping, containing
the approved ID, `last_seen_block`, sequence, and reached flag, then signs the
padded object containing a fresh placeholder.

WT gathers five current Pings and SAR acknowledgments. Each Pong contains the
other four Pings in peer order and its recipient's acknowledgment. A valid Pong
may increment the private counter and perform bounded height catch-up. Reaching
`mystery` permanently sets the withdrawal's reached flag. Reached peers continue
until WT distributes a valid all-reached collection.

All-reached evidence and full PSBT validation permit local MuSig2 signing between
Boomlet and Iso. Each peer produces a signed fragment; WT validates the complete
transaction assembled from five fragments and broadcasts the approved `tx_id`.
Fallback milestone eligibility follows the descriptor and current chain checks.

## 3. Changes to setup and WT authority

### 3.1 Immutable roster

Setup review includes the exact preference order of one to five `WtId` values.
Each identity contains a WT public key and Tor address. Keys and canonical
identities must be unique. ST displays complete addresses, roster positions,
and fixed public-key fingerprints without ambiguous truncation.

Index zero selects the initial WT. Only that service needs registration and
payment for setup to proceed. Optional dormant-service registration can reduce
later delay, at the cost of payment and metadata disclosure. A switch selects a
different index from the same roster. Changing an entry, its position, its key,
or an address without a setup-bound continuity mechanism requires a new setup
and fund rollover. SAR identities remain fixed.

### 3.2 Active head

Boomlet stores an active WT index and a 32-byte activation head. Define the hash
notation used below as:

```text
H(tag, fields...) = tagged_sha256(
  tag, canonical_encode(PROTOCOL_VERSION, fields...)
)

active_wt_index = 0
active_wt_head = H("Boomerang/wt/genesis", setup_instance_id)
```

A later head is the activation digest certified by five final decision votes.
It binds the exact predecessor, switch attempt, and candidate readiness content.
Returning to a previously used WT creates a different head.

Every state-advancing WT signature covers a tuple containing the active head
and its protocol content. This includes transaction approval, commit
acknowledgment, Pong, reached collection, and fragment or broadcast statements.
The expected signer comes from the stored active index. Immutable registration
receipts remain setup facts and are checked separately from current authority.

Active WT channel authentication uses:

```text
canonical_encode(message_type, ceremony_scope_id, active_wt_head)
```

The ceremony scope is the setup ID, withdrawal ID, or approved withdrawal ID
appropriate to that message. Authentication binds message type, traffic
direction, sender, and recipient. The head belongs in authenticated context;
the encrypted envelope need not gain another serialized field. Signed WT
content includes the head explicitly. Protocol version separates these signed
shapes from other profiles.

A receiver rejects a WT message with a different head, context, or signer.
Peer-authored approvals, commits, Pings, and signed fragments remain WT-neutral.
A current submission requires the originating Boomlet's authenticated channel,
or exact membership in that Boomlet's signed switch snapshot during reconstruction.
A historical signature alone cannot authorize a current submission.

### 3.3 Setup checkpoints and backup authority

The setup checkpoint chain remains a record of setup completion. A WT switch
has its own activation head. Candidate registration, required SAR finalization,
and exact outstanding placeholder acknowledgments are checked before preparing
activation, while completed setup checkpoints are retained. Uncompleted
WT-dependent prerequisites are repeated through the candidate.

Preserve the base one-time, normal-key-authorized encrypted backup to the
designated Boomletwo, including Iso's descriptor and SAR verification and the
source's `BackupDone` check. The target stays offline and inactive during normal
operation. A public archive cannot replace that backup or authorize activation.

The [Boomletwo proposal](boomlet_rollover.md) evaluates self-contained DIGGING
checkpoints encrypted to that same target and authenticated by existing Ping
signatures. It has no continuously online ST or backup requirement. The proposed
mutable-state export cannot change private setup policy, select a different
target or include secret MuSig2 nonces. Exact formats remain proposal work.

Backup activation must preserve exclusive authority, hidden votes, exact rescue
duties, replay history and delay protection. A signed checkpoint proves its
contents, not that no later state exists. Independent mystery generation cannot
silently spend a saved counter against a lower threshold. The proposal gives
conservative threshold policies, while source exclusion and concealed later
state remain unresolved activation requirements under the one-honest-peer model.
A checkpoint or peer report alone cannot enable signing or WT voting.

### 3.4 Peer WT discovery and self-inclusive Pong

Boomletwo can authenticate existing `WtReady` content against the WT head in a
source-signed checkpoint and derive that WT from the immutable roster. One
matching record suffices without new peer votes. It identifies the checkpoint's
WT; current authority still requires a justified decision history.

A candidate Pong format carries all five signed Pings, including the recipient's
own, while retaining its exact SAR acknowledgment separately. Normal Boomlet
compares its own returned Ping with its retained bytes; recovery verifies the
source signature. The other-four freshness predicate is unchanged. WT can sign
one shared Pong body, and detached recovery ciphertext avoids duplicating large
private snapshots inside every collection. This candidate requires a complete
version-selected wire definition before adoption.

## 4. Trigger, review, and frozen snapshot

### 4.1 Trigger

After sending a complete valid WT request, Niso tracks the height of the last
accepted state-specific response. A profile-defined silence threshold permits
proposing a switch. Generic heartbeats, duplicates, malformed traffic, or
responses missing required peer or SAR evidence do not refresh that progress
timer. Explicit user decisions or authenticated terminal errors may also trigger
a proposal. A timeout is advisory and changes no trusted authority.

For a request with a SAR acknowledgment, the host's monotonic elapsed timer must
exceed `SAR_ACK_DELAY + WT_SAR_PROCESSING_BUDGET + ROUND_TRIP_ROUTING_BUDGET +
CHAIN_OBSERVATION_BUDGET` before a silence prompt. Height silence alone cannot
establish that elapsed interval; rapid blocks cannot shorten a SAR deadline.
The [resource profile](resource_limits.md) fixes timer admission and retry rules.
Untrusted host time can suggest review but cannot advance the frozen journal.

Height decreases, contradictory RPC observations, or material disagreement with
the WT produce `CHAIN_VIEW_UNSAFE`. Otherwise the height policy supplies the
freshness and milestone checks used throughout the ceremony.

### 4.2 Snapshot and ST review

Before switching during signing, complete the exact live MuSig2 session or erase
its unused nonce through the signing abort procedure in Section 9. A produced
partial signature is retained as an immutable fragment.

Finish every already-required duress challenge before freezing. An accepted
answer is durably bound to its exact pending placeholder before another answer
can overwrite it. If the ordinary commit or Ping cannot yet be formed, retain
the answer and stall the freeze until its existing authorization gate can be
completed. User cancellation and service change cannot erase this duty. No new
challenge is drawn by switch preparation or obligation draining.

Boomlet constructs a manifest containing:

- setup ID, predecessor head, current WT identity and index, candidate identity
  and index;
- exact local phase, relevant ceremony identifiers, and the conditional recovery
  policy in Section 7;
- durable `digging_initialized` state;
- for DIGGING and later phases, accepted-Pong status and height, inherited
  predecessor height, current Ping digest and sequence, and public reached state;
- a digest of the local resume package;
- an explicit `NO_PLACEHOLDER` record or one exact outstanding placeholder
  commitment, including its approved ID, IV, padded-object digest, and gate
  evidence digest; unresolved state has no encodable absence value;
- retained completed-withdrawal IDs, so an idle peer cannot conceal signing or
  export state relevant to the proposed scope.

`digging_initialized` remains true through reached, signing, and retained export
state. An idle device after fragment export cannot report that the withdrawal
never entered DIGGING. A missing or contradictory state report is unresolved.

The resume package contains the public evidence needed for its phase:

| Local phase | Retained evidence |
| --- | --- |
| Setup | Parameter agreement, completed checkpoint certificate, and pending local setup receipts |
| No active withdrawal | Completed setup evidence and explicit absence of an active ceremony |
| Pre-DIGGING | Reviewed transaction commitment, local authorization state, and exact committed artifacts or their authenticated retention references |
| DIGGING | Accepted approval-set binding, local padded commit, current signed padded Ping, exact outstanding placeholder obligations, and accepted public progress summaries |
| Reached or signing | DIGGING evidence, reached collection, and signing-session disposition |
| Fragment collection | Immutable fragment, transaction binding, and retained public progress evidence needed by peers still completing the withdrawal |

Each phase has a fixed canonical layout, exact counts, and a maximum size.
Secrets including mystery, counter, placeholder plaintext, consent answers,
keys, and signing nonces stay on Boomlet. A host-provided object must match its
locally retained digest before Boomlet includes it. Candidate reconstruction
uses the exact committed bytes, with bounded external storage where appropriate.

```text
resume_digest = H("Boomerang/wt/local_resume",
                  phase, scope_kind, scope_id, local_resume_package)
review_commitment = H("Boomerang/wt/switch_review", manifest)
review_message = MessageWithNonce(review_commitment, fresh_32_byte_nonce)
```

`scope_kind` selects setup, withdrawal, or approved withdrawal; `scope_id` is
the corresponding identifier. `MessageWithNonce` carries the commitment and
its fresh review nonce as one signed value.

ST verifies the authenticated request and recomputes the commitment from the
supplied canonical manifest. It displays setup and ceremony identity, both WT
positions, addresses and fingerprints, and the recovery consequence. For a
pre-DIGGING peer, review authorizes fresh transaction review if nobody has
initialized DIGGING, or preservation if another peer already has. ST signs the
nonce-bound review only after user approval.

Ordinary state may continue while review is pending. On receiving ST's response,
Boomlet verifies the enrolled ST identity, signature, nonce, commitment, and
outstanding review. It rebuilds the manifest from its current state. Any change
requires a fresh review and nonce.

Before exporting its signed switch intent, Boomlet atomically stores the exact
intent, manifest, retention commitments, and frozen state. The intent signs the
same nonce-bound review message under a distinct signature domain. Queued WT
messages, ST answers, signing, and ordinary state advancement wait while frozen.
The sole withdrawal-side exception is verification and durable discharge of the
exact frozen placeholder under Section 5.2; it changes neither the signed
snapshot nor the ordinary phase, counters, heights, or sequences.
Crashes reproduce the same intent.

### 4.3 Common attempt

Peers exchange intents over authenticated paths independent of the old WT.
Every Boomlet verifies all five signatures in setup order, its own exact stored
intent, common setup and predecessor, the same reviewed candidate, compatible
scopes, and package commitments. Local transaction and phase checks remain
mandatory; another peer's advanced state cannot substitute for them.

```text
wt_switch_id = H("Boomerang/wt/switch_id", ordered_five_switch_intents)
```

The five fresh review nonces distinguish the attempt. Only the reviewed candidate
receives its setup and reconstruction evidence. Host-relayed artifacts are usable
only when their exact bytes occur in their originator's committed package.

## 5. Candidate preparation

### 5.1 Registration and service evidence

The candidate receives all five signed setup records, matching parameter
fingerprints, its roster identity, intent material, and required resume packages.
It verifies signatures, identifiers, membership, ordering, package hashes, and
phase prerequisites before retaining the reconstruction input durably.

Each Boomlet supplies its setup-bound signed SAR identity through the candidate
channel. If SAR finalization is incomplete, it also supplies its authenticated
SAR setup request. The candidate forwards requests to those exact SAR identities. Each Boomlet
verifies the inner SAR-signed finalization response in candidate-scoped transport
and retains it before initial PREPARE. This preparation needs no active-head WT
forwarding endorsement. Registration receipts bind setup ID and parameter fingerprint. SAR finalization
receipts bind setup ID, rescue-data identifier, and the stored encrypted-data
fingerprint. A returning candidate may reuse valid immutable registration evidence.

Payment information and receipts retain their service identity, invoice reference,
and payment-proof meanings. A new charge requires a distinct invoice and payment
replay checks. A new WT head alone does not require another charge.

Candidate channel authentication uses:

```text
canonical_encode("wt_candidate_registration", message_type,
                 setup_instance_id, wt_switch_id, candidate_wt_index)
```

Fresh outer encryption uses fresh IVs. Retained signed padded objects and their
inner placeholder envelopes remain byte-identical when retransmitted.

### 5.2 Discharge the frozen placeholder

Every peer retains at most one outstanding placeholder. Ordinary commit and Ping
creation persist the exact signed padded bytes and obligation before export;
another placeholder can be created only after its own exact acknowledgment is
verified. Transport retries reuse the same inner bytes and IV. An acknowledged
commit followed by an initial Ping therefore occupies one obligation slot.

Before ballot-zero ACTIVATE PREPARE in **every** continuation mode, each Boomlet
must either verify its retained exact SAR acknowledgment or establish from its
frozen journal that no placeholder is outstanding. The latter signs explicit
`NO_PLACEHOLDER` in its intent. Missing bytes, unknown acknowledgment state, a
pending challenge, or conflicting evidence stalls preparation.

The candidate reconstructs the gate-valid padded object from its originator's
committed package and transports the exact placeholder to the setup-bound SAR.
An independently authenticated relay can carry the same end-to-end envelope.
For an initiator commit the original complete approval set, exact WT approval,
and all four matching approval-set attestations are required before routing.
For a non-initiator commit, also retain its verified initiator acknowledgment.
Retained Ping evidence binds the initialized withdrawal and current sequence.
The host cannot replace this gate evidence with a claimed phase. Missing gates
stall preparation, including withdrawal closure.

Boomlet decrypts the ordinary SAR response and verifies the signature over its
exact pending envelope, approved withdrawal ID, setup-bound identity, and
ordinary SAR context. A switch-scoped candidate envelope can transport this
response; the inner SAR acknowledgment remains WT-neutral. A late old-WT packet
may be extracted by Niso and re-presented as this exact SAR response. Its old WT
signature cannot authorize any other transition. Discharge is atomically
journaled; duplicates require no second write. A SAR replay follows the ordinary
fixed release and idempotence rules, with identical safe and duress behavior.

The frozen five-record vector determines:

```text
obligation_digest = H("Boomerang/wt/obligations",
  ordered_five_frozen_obligation_records)
```

An ACTIVATE PREPARE attests that the signer has discharged its own listed duty
and checked the common vector against all five intents. A complete prepared
certificate supplies the five closure attestations. No additional Boomlet
signature round or acknowledgment-signature bytes enter the activation digest.
An honest peer's unresolved rescue signal therefore prevents preparation even
with four dishonest cosigners. A dishonest SAR can lie about processing; the
existing SAR trust assumption still applies.

Existing finalization receipts and actual placeholder acknowledgments supply
service evidence. Host health checks can inform routing but have no place in
activation authorization. A fresh route probe cannot strengthen the exact
placeholder proof or promise future SAR availability.

### 5.3 Readiness

After registration, payment, routing preparation, and durable reconstruction,
the candidate signs deterministic readiness content:

```text
ready_record = WtReady(scope, candidate_wt_index, recovery_mode,
                       closed_withdrawal_id, closed_approved_id,
                       obligation_digest)
ready_commitment = H("Boomerang/wt/candidate_ready", ready_record)

activation_digest = H("Boomerang/wt/activation",
  setup_instance_id, previous_active_wt_head, wt_switch_id, ready_commitment)
```

The candidate commits to the frozen obligation vector; each Boomlet enforces
its own discharge before PREPARE. Candidate readiness may arrive while an exact
SAR response is in flight, so no extra Boomlet readiness-report round is needed.

The activation certificate carries the valid candidate signature. The head hashes
the content commitment rather than signature bytes. A free timestamp or nonce
cannot vary the activation value within an attempt.

Before its initial activation PREPARE, each Boomlet verifies its own registration
and payment evidence, own discharged obligation, candidate signature, and phase
prerequisites. It independently derives `recovery_mode`, `closure_scope`, and
`obligation_digest` from the verified frozen intents. `closure_scope` names the
exact abandoned withdrawal ID and optional approved ID for closure; otherwise
it is the explicit absent variant.
Those checks are retained for decision recovery. Service expiry can stop an
initial PREPARE; it cannot revoke a completed certificate or add another live
service dependency to an already prepared decision.

## 6. Recoverable activation and cancellation

### 6.1 Scope, ballots, and values

```text
decision_scope = (PROTOCOL_VERSION, setup_instance_id,
                  previous_active_wt_head, wt_switch_id)
cancellation_digest = H("Boomerang/wt/switch_cancel",
  setup_instance_id, previous_active_wt_head, wt_switch_id)
```

The instance has exactly two permitted values, represented by a kind byte and
digest: `ACTIVATE(activation_digest)` and `ABORT(cancellation_digest)`.
`decision_ballot` is a durable u64 within the pending instance, initially zero.
It leaves the candidate, reviewed snapshot, and service head unchanged. Ballots
never wrap. The [resource limits](resource_limits.md) bound successor admission,
retries, total admitted ballots, and durable transactions.

PREPARE is provisional. Only five matching COMMIT signatures decide a value.
Decision COMMIT has a separate domain and meaning from withdrawal `TxCommit`.
It cannot substitute for transaction approval, a commit set, SAR acknowledgment,
or Pong.

### 6.2 Certificates

| Certificate | Required evidence |
| --- | --- |
| PreparedCertificate | Five PREPARE signatures over identical scope, ballot, and value |
| RecoveryCertificate | Five RECOVER reports for the same target ballot, each carrying its stated prepared certificate or explicit NONE |
| DecisionCertificate | Five COMMIT signatures over identical scope, ballot, and value, with committed intent material and candidate readiness evidence for ACTIVATE |

Every collection contains exactly one signature from each setup peer in setup
order. Recipients verify domains, versions, scope, counts, identities, signatures,
their own stored intent or recovery report, and the authorized decision value.

RECOVER signs the scope, target ballot, and its reported prepared vote content. A bounded sidecar supplies the five PREPARE signatures.
The reported certificate's ballot is strictly below the target. NONE has an
explicit absent tag. Certificate commitments cover scope, ballot, and value,
independently of signature encodings.

A final certificate need not repeat PREPARE signatures: every honest COMMIT
signer first verifies and durably retains them. A recovery collection carries at
most five prepared certificates. It does not recursively embed ballot history.
Each five-signature prepared certificate includes an honest witness that checked
its ballot justification before signing.

### 6.3 Successful activation

1. Collect the five reviewed intents and complete candidate preparation,
   including each signer's own exact placeholder discharge. For closure, every
   manifest must establish that DIGGING was never initialized and explicitly
   authorize abandonment of the same identifiers.
2. In ballot zero, each Boomlet persists and exports PREPARE for ACTIVATE.
   It signs at most one PREPARE value per ballot.
3. After receiving five matching PREPARE votes for its current ballot and its
   own prepared value, it verifies and durably retains that certificate as its
   highest locally accepted prepared certificate.
4. It then persists and exports COMMIT for the same scope, ballot, and value.
   COMMIT requires the current ballot, its matching PREPARE, and the complete
   prepared certificate. Another live candidate or SAR response is unnecessary.
5. Any peer assembles and distributes the final DecisionCertificate. Each Boomlet
   installs the new head and roster index atomically before accepting candidate
   traffic or applying the continuation in Sections 7 through 9.

Votes and certificates are durably disseminated among peers. The candidate cannot
be their sole holder. Partial final-certificate delivery leaves remaining peers
frozen until they verify the same final decision. Retransmission is idempotent.

### 6.4 Recovery

A trusted recovery request admits the next ballot within the same frozen
instance, subject to Section 10 and the resource profile. A host timeout alone
cannot persist a promise. The original ST review authorizes finishing that
reviewed candidate or canceling the attempt. A bounded automatic recovery allowance needs no second
ST approval; extending that allowance requires trusted local admission.

1. Before exporting RECOVER, Boomlet atomically persists a higher promised ballot
   and its exact report containing the highest prepared certificate locally
   accepted under Section 6.3, or NONE. That write forbids creating lower-ballot
   PREPARE or COMMIT votes.
2. Reports are immutable for their target ballot. Late lower-ballot certificates
   cannot rewrite them or authorize old COMMIT votes. Older certificates in
   another peer's report can justify a recovery value without reopening their
   original ballot. Retries reproduce the stored report.
3. Any peer or relay collects all five reports. Every Boomlet verifies the full
   collection, its own exact report, and target equal to its promised ballot.
4. If any valid prepared certificate is reported, select the value of the one
   with the highest ballot. Equal-highest certificates must agree on value.
   If every report is NONE, select ABORT. Each Boomlet computes the result itself.
5. Run PREPARE and COMMIT for the selected value in the target ballot. If delivery
   splits or a higher ballot intervenes, repeat recovery with retained evidence.

A signed claim that a peer prepared is insufficient. The report must contain the
actual five-signature certificate. Individual PREPARE votes do not force the
recovery result. No discretionary coordinator choice or coordinator signature
is needed to select it.

When recovery selects ACTIVATE, its certificate proves that all five peers
already checked their local prerequisites, or carried forward a certificate
establishing those checks. Recovery PREPARE and COMMIT use retained evidence even
if the candidate or SAR is unavailable. After installing a failed candidate,
peers can review another roster WT and switch from that new head. Ordinary
withdrawal progress still requires its service and chain checks.

When recovery selects ABORT, candidate cooperation is unnecessary. Boomlet
persists the final cancellation tombstone before unlocking the matching local
operation under the unchanged predecessor. It preserves DIGGING, pending duress
checks, outstanding placeholders, inherited spacing floors, and replay memory.
Verified obligation discharges survive ABORT; rollback of the freeze cannot
restore an acknowledged obligation or undo SAR activation.
A new attempt needs fresh ST reviews and nonces.

A valid final DecisionCertificate takes priority over recovery for the matching
unresolved instance, even when its ballot is below the local promise. Promises
restrict new votes; they do not prevent learning a completed decision. A decided
peer returns its final certificate instead of another RECOVER report. An old
certificate cannot roll back a later installed head.

### 6.5 Pending intents and durable state

An incomplete local intent can be withdrawn through fresh nonce-bound ST
cancellation approval or an equivalent trusted local user action, only before
its first PREPARE **and before its first RECOVER report**. Once it has reported,
remain frozen until a final decision. Archive its exact identity and withdrawn
tombstone. Host replay cannot recreate it as pending.

If peers later supply a complete set containing that withdrawn intent, its
originator may help close it through RECOVER and ABORT votes only. It reports
NONE because it never prepared that instance. A valid activation prepared
certificate cannot contain that honest peer's nonexistent PREPARE. Closing a
stale instance changes neither a different current operation nor its snapshot.

After PREPARE export, remain in the same instance until a final decision. Each
ballot permits at most one value per voting stage. A higher promise excludes
lower-ballot votes, and a new switch ID at the predecessor requires final ABORT or a locally
withdrawn intent that emitted neither PREPARE nor RECOVER. Admit at most one
live instance. Do not sign multiple five-intent combinations containing the same
local intent; persist the first accepted switch ID before any RECOVER or vote.
A withdrawn intent may close adversarial combinations only with ABORT. Process
one such closure at a time after any live instance finishes; each consumes a
trusted decision-instance reservation. These closures cannot unlock or modify
another operation. Local tombstone matching precedes cryptographic processing.

Persist the promised ballot, highest complete prepared certificate, exact current
report and own votes, prerequisite commitments, and final decision before their
corresponding outputs. Keep the highest certificate's five signatures durably
available on Boomlet; a host-held digest alone cannot support recovery. Replacing
that certificate with a higher valid one is atomic.

A crash before export can retain a vote or promise nobody received. Exact replay
recovers it. A crash after export cannot forget it. Retain final certificates or
equivalent authenticated recoverable evidence for peer catch-up. Storage failure,
unresolved writes, missing evidence, or ballot exhaustion stalls safely.

### 6.6 Safety and completion

A prepared value controls recovery only through its complete certificate. A
COMMIT signer retains that certificate, and every recovery collection includes
the honest signer's report or learns its final decision. Higher promises prevent
old votes, so authentic signatures, collision-resistant commitments, correct
validation, and one durable honest identity exclude conflicting final values.
The [verification report](security_verification.md) gives the full argument.

Completion still requires all five peers, retained evidence, finite resources,
and eventual agreement on one ballot. Different intent locks at honest peers can
prevent either combination from collecting five reports. Preserve those locks
and use fallback; unilateral rebinding would permit conflicting heads.

## 7. Continuation during setup and before DIGGING

### 7.1 Interrupted setup and an idle setup

| Failure stage | Continuation after ACTIVATE |
| --- | --- |
| Before parameter agreement | Finish a consistent reviewed setup agreement before deriving its roster-bound genesis and using failover |
| `PARAMETERS_AGREED` | Verify candidate registration and local receipt, then complete the matching WT-ready checkpoint exchange |
| `WT_READY` | Preserve completed checkpoints, verify retained candidate-path SAR finalization evidence, and complete the SAR-ready checkpoint exchange |
| `SAR_READY` | Preserve completed checkpoints; finish designated encrypted backup, ordinary Iso checks and `BackupDone` |
| `BACKUP_READY` or partial final delivery | Verify and relay matching completed checkpoint evidence; finish each local completion guard |
| Setup complete, no withdrawal active | Install the head and use it for the next withdrawal |

Partial checkpoint delivery is resolved from exact signed evidence. A peer's
reported phase alone cannot complete another peer's checkpoint. Pending
WT-specific receipts are checked against the candidate whenever their local
prerequisite must be repeated. A final ABORT resumes the matching frozen setup
operation under its predecessor head.

### 7.2 Recovery mode

The five frozen manifests select a deterministic policy:

```text
all five establish no active withdrawal:
    change service only
all five establish compatible withdrawal state with DIGGING never initialized:
    CLOSE_PRE_DIGGING_WITHDRAWAL
any initialized DIGGING and all scopes can be reconciled:
    PRESERVE_WITHDRAWAL
otherwise:
    stall
```

Incomplete authorization reports bind the withdrawal under discussion and each
peer's actual participation. A completed archive matching another peer's active
scope is reconciled by supplying the exact full signed transaction before freezing. That peer verifies
its completion and local SAR duties; a phase claim cannot substitute for the
transaction. An unmatched closed scope stalls review. A missing approved ID has
a phase-specific meaning; it is not permission to erase unexplained later state. A false initialized report
can stall a restart. False negative reports cannot reset an honest peer's delay.

### 7.3 Close a pre-DIGGING withdrawal

Before initial PREPARE, every signed intent explicitly authorizes the exact
closure scope and all five snapshots establish `digging_initialized == false`.
Section 5.2 discharges each frozen obligation, including a padded commit that
the predecessor WT accepted but never forwarded. The readiness commitment and
every activation vote cover the common closure scope and obligation vector.
An unresolved or missing scope, prepared placeholder, or signing archive stalls
closure. If any peer has initialized DIGGING, preserve that withdrawal.

After final ACTIVATE, atomically tombstone the abandoned withdrawal ID and any
approved ID, invalidate its pending transaction and duress-review nonces, and
retire its local active state before unlocking. A new withdrawal uses fresh
ordinary ST transaction review, a fresh initiator nonce, approvals, and commits.
The proposed transaction may be identical, but switch approval does not approve
that transaction. Historical approval-set continuation is outside this profile.

A final ABORT keeps the original operation and its still-valid local reviews.
Already completed rescue activation is irreversible. Each honest peer has
verified all its committed obligations before any activation certificate can be
prepared. Delayed duplicate responses cannot resurrect a closed withdrawal.

Bound tombstones and attempt admission without evicting an ID while replay could
still authorize an action. Exhaustion stalls new attempts. Restart simplifies
historical freshness handling but repeats user reviews and ordinary signatures.

### 7.4 Mixed DIGGING entry

If any peer has initialized DIGGING, all initialized peers retain their approved
transaction, both withdrawal IDs, mystery, counter, heights, sequences, reached
state, and duress obligations. A lagging peer enters DIGGING exactly once after:

1. Its own durable state establishes acceptance of the same approval set and
   creation of its exact commit through the initiator-first gates in Section 2.
2. The candidate reconstructs the five exact signed padded commits from the
   originating peers' committed packages, verifies signatures and approved ID,
   and routes their exact placeholders to the fixed SARs.
3. The peer verifies the complete `COMMIT_SET` handoff, its own exact SAR
   acknowledgment, final activation certificate, and a new-head WT commit response.
4. Local descriptor, milestone, chain-safety, and phase conditions hold.

`COMMIT_SET` is the only historical phase-advancing package in this profile.
Its historical timestamps describe the committed snapshot. The exception is
limited to elapsed block age of (1) the five exact `TxCommit.event_block_height`
values and (2) the retained predecessor initiator commit acknowledgment and WT
approval used only to verify their already-satisfied gate. These objects must
be byte-identical to the committed packages and locally recorded authorization.

No approval, duress answer, or new commit may be created through this exception.
Retained `TxApproval` values prove the already accepted set; they cannot advance
an incomplete approval phase. Future-height rejection against the safe current
chain view remains mandatory for all historical heights. Fresh candidate commit
responses use the ordinary age window. All signatures, domains, versions, setup
and withdrawal IDs, five-peer order, approval-set gates, exact own SAR response,
current head, descriptor, milestones, local phase, and single initialization
checks remain mandatory. SAR acknowledgments have no block-height field and
verify by exact-envelope replay rules. Ping sequences, Pong age and spacing,
ST nonces, signing sessions, service expiry, and chain safety receive no freshness
exception. Missing evidence stalls.

## 8. DIGGING continuation

### 8.1 Outstanding obligations and recovery Ping

Initial activation preparation discharges the frozen placeholder under Section
5.2. Installation retains that discharge, including after candidate loss and
decision recovery. An already acknowledged placeholder requires no replay.
Recovery Pings create the next ordinary SAR obligation under the installed head.

A required duress challenge from an accepted ordinary Pong must finish before
creating another Ping. Preserve these challenges and outstanding placeholder
records through cancellation and repeated switches. A newer safe placeholder
cannot replace an unacknowledged duress placeholder.

Each initialized Boomlet then creates at most one recovery Ping per new head
without receiving another Pong first. It uses the next unused sequence, retained
height and reached flag, and fresh placeholder encryption over current local
plaintext. Persist the signed padded bytes and sequence update before export;
a crash retransmits that same Ping. Waiting for prior acknowledgments prevents
repeated switches from accumulating outstanding recovery placeholders.

Recovery-Ping creation changes neither mystery, counter, nor local height and
draws no new duress challenge. A newly initialized lagging peer sends its normal
initial Ping. Every other peer's recovery Ping is newer than anything it emitted
before its snapshot froze, including after partial old-Pong delivery.

### 8.2 Pong spacing and validation

The five manifests report accepted-Pong status, last accepted event height, and
any inherited predecessor height. Each Boomlet checks its own report against
durable state and derives the maximum reported predecessor height `F`.

```text
first_new_pong.event_block_height >= F + MIN_PONG_SPACING_BLOCKS
```

`F` is a predecessor height, not a next-eligible height; applying recovery
repeatedly must not compound the same wait. Preserve it across a switch with no
intervening accepted Pong and across cancellation. The first-Pong exemption
applies only when every report says no accepted Pong, no inherited floor exists,
and local state agrees. Unknown history or unsafe heights stalls. A malicious
report cannot lower an honest peer's stored floor; inflated heights can cause
denial of service and remain subject to chain checks.

Each Pong must satisfy all of the following:

- expected active WT signer and authenticated head, message type, and scope;
- the same approved withdrawal ID and acceptable event-height freshness;
- one signed Ping from each of the other four setup peers, in order;
- strictly increasing remembered peer sequences and monotonic reached flags;
- the recipient's exact SAR acknowledgment for its outstanding placeholder;
- inherited spacing and monotonic local and WT heights, with safe chain views.

Before updating its local height, Boomlet increments `counter` only if the local
Niso height `h` exceeds `last_seen_block` and every other peer's included Ping
height lies within `[h - PEER_PING_HEIGHT_TOLERANCE, h]`. Reached peers' current
Pings remain eligible. An otherwise valid Pong performs bounded catch-up:

```text
last_seen_block = min(h, last_seen_block + MAX_HEIGHT_CATCHUP_BLOCKS)
```

This update applies when the local height lags `h`. Each valid Pong produces the
next ordinary Ping, with a fresh placeholder IV, even when the counter predicate
is false. The ordinary per-round duress draw occurs once; a selected challenge
finishes before creating that next placeholder. Invalid Pongs and unsafe chain
views stall state advancement.

The spacing, tolerance, and catch-up names above denote positive profile
parameters. Activation and recovery-Ping creation never increment counters.
A valid increment already accepted from a partially delivered old round remains;
peers that missed it invent none. Old Pongs cannot advance state under a new head.

### 8.3 Reached evidence

The candidate obtains five fresh post-activation reached Pings and routes their
placeholders before distributing a current-head reached collection with each
recipient's own exact encrypted SAR acknowledgment. Boomlets verify that
acknowledgment and all five identities, signatures, sequences, approved IDs,
and true reached flags. The same acceptance path applies when all peers had reached before the
switch. Further Pong rounds are unnecessary once that collection is valid.

## 9. Signing, fragments, and broadcast

Before entering signing, Boomlet checks that the PSBT inputs match the setup
descriptor, its transaction identity matches the reviewed one, all reached
evidence is valid, and milestone eligibility holds. Hydration may add signing
metadata but preserves version, locktime, input outpoints and sequences, output
scripts and amounts, and input and output order. Boomerang inputs require
`SIGHASH_DEFAULT`.

A live MuSig2 session binds message, aggregate key, participants, tweaks, public
nonces, and session context. Finish that exact session before freezing a switch,
or erase unused secret nonces and record its abort. A fresh signing attempt uses
fresh nonces. A consumed nonce is never used for another partial-signature attempt,
including on the same message. A completed partial signature is replayed only as
its immutable retained fragment.

After activation, peers still needing signatures verify current reached evidence
and the PSBT before signing. Peers with completed fragments retain them and the
public progress state needed by unfinished peers. Retain pending duress state
and placeholder obligations until those duties finish. Export alone cannot
turn a signing withdrawal into a restartable pre-DIGGING attempt.

Boomlet atomically retains its exact fragment before export, together with the
approved IDs, transaction commitment, initialized flag, signing disposition,
current Ping and replay state, and pending security duties. Niso stores a copy
and forwards a Boomlet-authenticated current-head submission. A crash after
export retransmits the same fragment; it never authorizes another signing pass.

The active WT durably stores the exact fragment before signing a head-bound
`FragmentReceipt` naming setup, approved ID, origin peer, and fragment digest.
The originating Boomlet checks the receipt against its retained bytes. Receipt
acceptance records dissemination only. Because Niso and WT may both be malicious,
neither their receipt nor a broadcast claim permits Boomlet to erase its copy.

To finish a ceremony, Boomlet streams and verifies the complete transaction
assembled from the five retained signed fragments, descriptor, signatures and
approved `tx_id`, and verifies its own latest placeholder acknowledgment. The
WT's head-bound `CompletionReceipt` records storage of those exact transaction
bytes and ordered fragment digests. Receipt acceptance records dissemination;
the verified complete transaction and local discharge themselves authorize
`SIGNATURE_EXPORTED` to move to `COMPLETED_RETAINED`. All five valid fragments prove
that each honest signer completed its local signing gates. A pending challenge
or outstanding placeholder blocks completion. Receipt retransmission is
idempotent and performs no additional persistent write.

At `COMPLETED_RETAINED`, erase consumed signing secrets and private mystery and
counter, invalidate reviews, and retain a durable closed-withdrawal record plus
the exact local fragment. The archived `digging_initialized` flag stays true.
An initialized peer that lacks the final transaction may use an authenticated
holder's exact complete transaction to finish its ordinary validation, even if
its installed head differs; transaction verification is WT-neutral. A closed
peer supplies its immutable fragment and complete transaction evidence instead
of creating a new Ping. If any honest peer still needs to sign, no valid complete
transaction can exist, so every honest exported peer still retains the public
state needed for fresh reached Pings.

Four archive slots are reserved before admitting withdrawals. Retained local
fragments survive later withdrawals and WT changes until permanent retirement
of the setup identity, or stay indefinitely when retirement cannot be established.
Public copies at Niso, WT, and another peer improve availability; the honest
originator's own retained bytes are the recovery anchor. Full archive slots
stall new withdrawals while leaving replay and pending recovery usable. Setup
retirement atomically disables every protocol operation for that identity
before erasing archives, and requires completed local rescue duties and trusted
approval of permanent setup abandonment with the verified rollover or fallback
spend. Retirement forbids reuse of that identity and descriptor for new funding. It cannot be inferred from a WT broadcast claim.

A fully signed retained transaction can be verified and rebroadcast with the
same `tx_id` by its holder. A duplicate broadcast does not authorize different
outputs or another signing attempt. WT service-authority changes still follow
the reviewed decision procedure.

## 10. Domains, storage, and workload

### 10.1 Signature domains

The [wire contract](wire_contract.md) defines every signature domain, content
type, transport context, record layout, absent variant, and bound. Decoders
enforce the selected profile, type, order, count, nesting, and domain before
expensive processing. Cross-profile signatures and envelopes are invalid.

### 10.2 Retention and validation

Boomlet keeps the roster, active head and index, frozen local manifest, exact
exported control statements, promised ballot, highest prepared certificate,
final decision, recovery-Ping replay state, required ceremony secrets, and
bounded tombstones. Persistent writes precede corresponding outputs.

Niso retains public packages, vote collections, setup evidence, and fragments.
Candidate WT retains reconstruction inputs, route records, certificates, and
replay state. Their data remain untrusted and require verification. Stream
bounded artifacts against stored digests rather than loading five full transcripts
into Boomlet. Digests protect integrity; durable holders supply availability.

Niso rejects malformed sizes, identities, contexts, signatures, transaction data,
and visible replay violations before invoking Boomlet. Boomlet independently
checks every condition that authorizes its own transition. Protected caches can
reuse verification of identical artifacts in one frozen context; relevant state
changes invalidate them. A host's validity flag is insufficient.

### 10.3 Workload

| Operation | Added control work |
| --- | --- |
| Successful switch | Three Boomlet signatures per peer, fifteen total: intent, PREPARE, COMMIT |
| ST review | One signature and one Boomlet verification per peer |
| Candidate readiness | One signed deterministic commitment |
| Frozen obligation discharge | At most one exact SAR acknowledgment verification per Boomlet; reuse an already verified acknowledgment |
| Recovery ballot | Up to one RECOVER, PREPARE, and COMMIT signature per peer, plus recovery-certificate verification |
| DIGGING continuation | Up to five fresh padded Pings and SAR exchanges, plus unresolved placeholder replay |
| Pre-DIGGING closure | Existing intent and PREPARE carry closure authorization and discharge attestation |
| New withdrawal after closure | Fresh transaction reviews, approvals, and commits |
| Completion | Stream final transaction once and retain own immutable fragment; a WT receipt records dissemination |

Each padded Ping has two Boomlet signatures. Certificate verification, hashing,
encryption, channel operations, interface traffic, and durable writes add further
cost. Bound and measure complete workloads, maximum package sizes, journal bytes,
memory, latency, and write endurance on the intended hardware. Concrete admission
limits, fixed storage reservations, and recovery allowances are specified in
[resource_limits.md](resource_limits.md). Duplicate control messages use protected
cached results. Prepared sidecars with identical content are verified once per
frozen instance, with no recursive history or duplicate stored certificates.

## 11. Companion sequence diagrams

Arrows show logical authenticated messages. Niso relays are abbreviated where
they do not affect the ordering being illustrated. A grouped peer lifeline denotes
independent operations by the named peers, with five distinct signatures and
local prerequisite checks wherever a five-peer collection is required. Diagram
references abbreviate the common exchange defined in Sections 4 through 6.

| Diagram | Coverage |
| --- | --- |
| [01_setup_changes.puml](01_setup_changes.puml) | Roster review, genesis binding, initial registration, SAR finalization, and backup additions |
| [02_common_switch.puml](02_common_switch.puml) | Review, freeze, candidate preparation, obligation discharge, PREPARE, COMMIT, and head installation |
| [03_setup_failover.puml](03_setup_failover.puml) | Interrupted setup checkpoints and an idle completed setup |
| [04_predigging_failover.puml](04_predigging_failover.puml) | Closure before any mystery initialization and selection of preservation for mixed states |
| [05_mixed_digging_failover.puml](05_mixed_digging_failover.puml) | Exact commit handoff to lagging peers while initialized peers retain their delay |
| [06_digging_failover.puml](06_digging_failover.puml) | Partial Pong delivery, outstanding placeholders, recovery Pings, spacing, and reached evidence |
| [07_decision_recovery.puml](07_decision_recovery.puml) | Cancellation, higher promises, certificate selection, and candidate failure during a decision |
| [08_signing_and_broadcast_failover.puml](08_signing_and_broadcast_failover.puml) | Ready-to-sign, live nonce handling, retained fragments, aggregation, and broadcast |

## 12. Validation and adoption

The [verification report](security_verification.md) records model bounds,
results, negative controls, and the open real-chain observation blocker. The
[issue register](security_issues.md) maps findings to controls, and
[security requirements](security_requirements.md) define adoption integration.

Deployment still requires complete wire and cryptographic vectors, integrated
state-machine verification, independently reviewed firmware, power-loss and
anti-rollback evidence, and hardware measurements. Bounded model success is not
production approval.

The underlying prepare, commit, and recovery pattern is informed by
[Castro and Liskov's authenticated agreement construction](https://static.usenix.org/publications/library/proceedings/osdi99/full_papers/castro/castro_html/node4.html).
The five-of-five certificate rule and its availability assumptions are specific
to this proposal. MuSig2 nonce and session requirements follow
[BIP 327](https://bips.dev/327/).
