# WT failover

A setup authorizes an ordered roster of one to five Watchtowers. All five peers
can replace the active Watchtower with another roster member through a reviewed,
signed decision. The replacement prepares its service before activation, and
each Boomlet preserves its withdrawal security state throughout the change.

This is a protocol proposal. Wire encodings, resource limits, full protocol
verification, and hardware measurements remain adoption requirements.

## 1. Participants and security boundary

| Participant | Responsibility |
| --- | --- |
| User | Reviews service identities and transactions on a trusted display |
| Boomlet | Secure element holding a peer's identity key, signing share, private withdrawal state, and durable protocol journal |
| Secure Terminal, ST | Trusted display and input device; signs the user's nonce-bound review |
| Niso | Online host that handles networking, transaction data, and local chain observations; its claims cannot authorize Boomlet state changes |
| Iso | Offline device holding the user's normal signing key and participating in local MuSig2 signing with Boomlet |
| Watchtower, WT | Coordinates five peers, checks public evidence, routes placeholders, collects signatures, and broadcasts the approved transaction |
| Secure Automatic Rescuer, SAR | Holds encrypted rescue data and processes a peer's encrypted duress placeholders |
| Boomletwo | Inactive backup device; it requires source-device revocation and authoritative journal recovery before becoming active |

There are exactly five peers, each with its own Boomlet, ST, Niso, and setup-bound
SAR identity. A WT roster can contain fewer than five entries. A one-entry roster
has no replacement service.

Every activation certificate requires all five Boomlets. Safety assumes at least
one honest Boomlet whose identity has no active clone and whose persistent state
cannot be rolled back. Compromised peers may lie about their own state, and a
compromised Niso or WT may alter, delay, replay, or suppress traffic. Each honest
Boomlet independently enforces its own authorization and progress conditions.

Completion requires all five peers to cooperate and eventually communicate.
Preparing a replacement additionally requires the reviewed WT, the setup-bound
SARs, required service payments, user interaction, and safe chain observations.
Recovery of a partly voted decision uses retained peer evidence and can finish
without another response from the candidate or SAR.

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
| `BACKUP_READY` | Local authenticated backup receipt and five matching checkpoint signatures |

Each checkpoint binds the setup ID, phase label, and previous checkpoint. Local
receipts are prerequisites for signing it; peer-specific receipts are separate
from the checkpoint hash. A lone checkpoint signature is pending evidence until
the complete matching collection is verified.

### 2.2 Transaction authorization

A withdrawal begins with a transaction represented as a partially signed Bitcoin
transaction, or PSBT. Each user reviews its transaction identity on ST. The
initiator generates a fresh approval nonce, and the participants derive:

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

All five approvals must name the same withdrawal and appear in setup peer order.
Each non-initiator attests that it verified the complete approval set and the WT
approval. Those attestations bind the WT approval actually checked.

The initiator then signs a `TxCommit` carrying the approved withdrawal ID. Its
signed commit is padded with an encrypted duress placeholder, and the combined
object is signed again. The WT verifies all four non-initiator approval-set
attestations before routing the initiator's placeholder or acknowledging its
commit. Each non-initiator creates its commit only after verifying that WT
acknowledgment. Every Boomlet verifies all five commits and its own exact SAR
acknowledgment before entering DIGGING.

### 2.3 Duress and DIGGING

The placeholder encrypts either safe plaintext or a rescue activation key for
the peer's fixed SAR. It is present on every commit and Ping path. SAR signs the
exact encrypted placeholder and returns that signature encrypted to Boomlet.
The acknowledgment exposes no classification status.

SAR uses the same fixed acknowledgment release delay, durable record shape, and
retry behavior for safe and duress processing. Exact replay is idempotent under
the approved withdrawal ID, Boomlet identity, and placeholder IV. A committed
rescue activation is irreversible.

On first DIGGING entry, Boomlet samples a private random threshold `mystery`,
sets `counter` to zero, initializes its height and Ping sequence, and records
that initialization durably. Each Ping contains the approved withdrawal ID,
local `last_seen_block`, sequence, and reached flag. Boomlet signs the Ping and
then signs the padded object containing its freshly encrypted placeholder.

WT gathers five current Pings and their SAR acknowledgments. It sends each
recipient a Pong containing the other four signed Pings in peer order and that
recipient's own encrypted acknowledgment. A valid Pong may advance the private
counter and perform bounded height catch-up. The counter reaching `mystery`
makes the reached flag permanently true for that withdrawal. Reached peers
continue providing Pings until a valid all-reached collection is distributed.

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

### 3.3 Setup checkpoints and backups

The setup checkpoint chain remains a record of setup completion. A WT switch
has its own activation head. Candidate registration and fresh SAR evidence are
verified before activation, while completed setup checkpoints are retained.
Uncompleted WT-dependent prerequisites are repeated through the candidate.

Backup replay state includes the active head, selected index, and authoritative
switch journal. A completed certificate can synchronize a completed head, but
cannot reveal a source device's unexported vote or higher-ballot promise.
Boomletwo therefore requires source revocation and resolution of every pending
decision before signing an intent, decision vote, or WT-sensitive statement.

Existing setups lacking the genesis binding, authenticated WT head, and durable
decision state require a new setup to acquire this protocol.

## 4. Trigger, review, and frozen snapshot

### 4.1 Trigger

After sending a complete valid WT request, Niso tracks the height of the last
accepted state-specific response. A profile-defined silence threshold permits
proposing a switch. Generic heartbeats, duplicates, malformed traffic, or
responses missing required peer or SAR evidence do not refresh that progress
timer. Explicit user decisions or authenticated terminal errors may also trigger
a proposal. A timeout is advisory and changes no trusted authority.

Height decreases, contradictory RPC observations, or material disagreement with
the WT produce `CHAIN_VIEW_UNSAFE`. Otherwise the height policy supplies the
freshness and milestone checks used throughout the ceremony.

### 4.2 Snapshot and ST review

Before switching during signing, complete the exact live MuSig2 session or erase
its unused nonce through the signing abort procedure in Section 9. A produced
partial signature is retained as an immutable fragment.

Boomlet constructs a manifest containing:

- setup ID, predecessor head, current WT identity and index, candidate identity
  and index;
- exact local phase, relevant ceremony identifiers, and the conditional recovery
  policy in Section 7;
- durable `digging_initialized` state;
- for DIGGING and later phases, accepted-Pong status and height, inherited
  predecessor height, current Ping digest and sequence, and public reached state;
- a digest of the local resume package.

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
messages, ST answers, signing, and all other state advancement wait while frozen.
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
SAR setup request. The candidate forwards requests to those exact SAR identities.
Registration receipts bind setup ID and parameter fingerprint. SAR finalization
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

### 5.2 Fresh SAR probe

Each Boomlet sends an authenticated challenge to its SAR through the candidate:

```text
probe_digest = H("Boomerang/wt/sar_route_challenge",
  setup_instance_id, previous_active_wt_head, wt_switch_id,
  candidate_wt_index, boomlet_identity_pubkey, setup_bound_sar_id)
```

SAR authenticates the Boomlet and setup, signs the exact digest under the route
probe response domain, and encrypts its response to Boomlet. Request and response
use distinct authenticated message contexts bound to the switch; candidate-facing
transport also binds the candidate. Every Boomlet verifies its own response.

Freshness comes from the unique switch ID. The probe performs no duress
classification or rescue activation, and cannot satisfy a placeholder
acknowledgment. Its behavior is independent of safe or duress state. It establishes
a SAR response for this attempt through the selected transport; it cannot establish
independent infrastructure or future availability.

The request uses the existing authenticated Boomlet-to-SAR channel, adding no
Boomlet signature. Each Boomlet verifies one fresh SAR response signature.

### 5.3 Readiness

After registration, payment, routing preparation, and durable reconstruction,
the candidate signs deterministic readiness content:

```text
ready_commitment = H("Boomerang/wt/candidate_ready",
  setup_instance_id, previous_active_wt_head, wt_switch_id, candidate_wt_id)

activation_digest = H("Boomerang/wt/activation",
  setup_instance_id, previous_active_wt_head, wt_switch_id, ready_commitment)
```

The activation certificate carries the valid candidate signature. The head hashes
the content commitment rather than signature bytes. A free timestamp or nonce
cannot vary the activation value within an attempt.

Before its initial activation PREPARE, each Boomlet verifies its own registration
and payment evidence, fresh SAR probe, candidate signature, and phase prerequisites.
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
never wrap, and the profile bounds admissible jumps, retries, and writes.

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

RECOVER signs the scope, target ballot, and a commitment to its reported
certificate content. A bounded sidecar supplies the five PREPARE signatures.
The reported certificate's ballot is strictly below the target. NONE has an
explicit absent tag. Certificate commitments cover scope, ballot, and value,
independently of signature encodings.

A final certificate need not repeat PREPARE signatures: every honest COMMIT
signer first verifies and durably retains them. A recovery collection carries at
most five prepared certificates. It does not recursively embed ballot history.
Each five-signature prepared certificate includes an honest witness that checked
its ballot justification before signing.

### 6.3 Successful activation

1. Collect the five reviewed intents and complete candidate preparation.
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

A timeout or cancellation request starts a higher ballot within the same frozen
instance. The original ST review authorizes finishing that reviewed candidate
or canceling the attempt, so recovery requires no second ST approval.

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
A new attempt needs fresh ST reviews and nonces.

A valid final DecisionCertificate takes priority over recovery for the matching
unresolved instance, even when its ballot is below the local promise. Promises
restrict new votes; they do not prevent learning a completed decision. A decided
peer returns its final certificate instead of another RECOVER report. An old
certificate cannot roll back a later installed head.

### 6.5 Pending intents and durable state

An incomplete local intent can be withdrawn through fresh nonce-bound ST
cancellation approval or an equivalent trusted local user action, only before
its first PREPARE. Archive its exact identity and withdrawn tombstone. Host
replay cannot recreate it as pending.

If peers later supply a complete set containing that withdrawn intent, its
originator may help close it through RECOVER and ABORT votes only. It reports
NONE because it never prepared that instance. A valid activation prepared
certificate cannot contain that honest peer's nonexistent PREPARE. Closing a
stale instance changes neither a different current operation nor its snapshot.

After PREPARE export, remain in the same instance until a final decision. Each
ballot permits at most one value per voting stage. A higher promise excludes
lower-ballot votes, and a new switch ID at the predecessor requires final ABORT.

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

If A has only prepared activation while B requests cancellation, reports with no
complete prepared certificate lead to ABORT in a higher ballot. A's provisional
vote can be superseded, and its higher promise prevents an old COMMIT.

If A already emitted COMMIT, it retained the complete prepared certificate first.
Every valid recovery collection includes its report or learns its final decision.
Recovery therefore preserves that activation. B can finish with the certified
prerequisites even after candidate failure.

For any final decision, including a withheld certificate, there is an honest
COMMIT signer retaining its prepared certificate. Recovery cannot omit that
signer's report. A conflicting higher prepared certificate cannot be the first
exception, because creating it also needs the honest PREPARE after a valid
recovery collection. Two conflicting certificates in one ballot require an
honest double PREPARE. Thus different final values cannot both be certified.

The argument assumes authentic signatures, collision-resistant commitments,
correct validation, and one authoritative honest identity with durable state.
All five peers must cooperate for completion, retain required evidence, and
eventually share a ballot long enough for delivery. Increasing timeouts and
retransmission support convergence. A withholding peer, endless message loss,
forced ballot churn, device loss, or exhausted resources can still prevent it.

## 7. Continuation during setup and before DIGGING

### 7.1 Interrupted setup and an idle setup

| Failure stage | Continuation after ACTIVATE |
| --- | --- |
| Before parameter agreement | Finish a consistent reviewed setup agreement before deriving its roster-bound genesis and using failover |
| `PARAMETERS_AGREED` | Verify candidate registration and local receipt, then complete the matching WT-ready checkpoint exchange |
| `WT_READY` | Preserve completed checkpoint evidence, finalize the same SARs through the candidate, and complete the SAR-ready checkpoint exchange |
| `SAR_READY` | Preserve the completed checkpoints and perform the authenticated backup procedure, including current head and replay state |
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
    RESTART_PRE_DIGGING
any initialized DIGGING and all scopes can be reconciled:
    PRESERVE_WITHDRAWAL
otherwise:
    stall
```

Incomplete authorization reports bind the withdrawal under discussion and each
peer's actual participation. A missing approved ID has a phase-specific meaning;
it is not permission to erase unexplained later state. A false initialized report
can stall a restart. False negative reports cannot reset an honest peer's delay.

### 7.3 Pre-DIGGING restart

After final ACTIVATE, atomically tombstone the abandoned withdrawal ID and any
approved ID, invalidate its pending transaction and duress-review nonces, and
retire its local active state before unlocking. A new withdrawal uses fresh
ordinary ST transaction review, a fresh initiator nonce, approvals, and commits.
The proposed transaction may be identical, but switch approval does not approve
that transaction. Historical approval-set continuation is outside this profile.

A final ABORT keeps the original operation and its still-valid local reviews.
Already delivered or later replayed old placeholders can still cause irreversible
SAR rescue activation. Abandonment cannot recall them.

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
Its old timestamps describe the committed snapshot. The final wire specification
must enumerate which historical age checks this proof replaces. Fresh WT
responses still obey ordinary age limits. Missing evidence stalls; a peer's
initialized flag alone cannot authorize another peer's DIGGING entry.

## 8. DIGGING continuation

### 8.1 Outstanding obligations and recovery Ping

After installing the head, first resolve every retained placeholder obligation.
The candidate replays exact outstanding inner placeholders to the same SAR;
each Boomlet verifies its own encrypted acknowledgment of those exact bytes.
The candidate forwards the acknowledgment in switch-scoped or active-head
transport. Accepting it retires only that obligation and changes no counter.
Already acknowledged placeholders require no replay solely for route freshness.

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
placeholders before distributing a current-head reached collection. Boomlets
verify all five identities, signatures, sequences, approved IDs, and true reached
flags. The same acceptance path applies when all peers had reached before the
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

Niso retains each fragment durably. Its originating Boomlet authenticates the
new-head submission envelope, which Niso forwards to the candidate.
The candidate verifies all five peer signatures, descriptor, complete transaction,
and approved `tx_id` before broadcast. Retain enough copies of fragments and
completion evidence for recovery; loss at every holder cannot be reconstructed
from a digest. The final specification must define durable fragment and
completion receipts before allowing corresponding evidence to be erased.

A fully signed retained transaction can be verified and rebroadcast with the
same `tx_id` by its holder. A duplicate broadcast does not authorize different
outputs or another signing attempt. WT service-authority changes still follow
the reviewed decision procedure.

## 10. Domains, storage, and workload

### 10.1 Signature domains

| Signed statement | Domain |
| --- | --- |
| ST switch review | `Boomerang/wt/switch_review` |
| Boomlet intent over the same nonce-bound message | `Boomerang/wt/switch_intent` |
| Candidate readiness commitment | `Boomerang/wt/candidate_ready` |
| SAR route response | `Boomerang/wt/sar_route_probe` |
| Decision PREPARE | `Boomerang/wt/decision_prepare` |
| Decision COMMIT | `Boomerang/wt/decision_commit` |
| Decision RECOVER | `Boomerang/wt/decision_recover` |
| Trusted withdrawal of an incomplete intent | `Boomerang/wt/pending_intent_cancel_review` |

Generic signed and encrypted wrappers carry exact protocol-version-specific
tuples. Decoders enforce the expected type, order, count, nesting, and domain
before expensive processing. The wire specification must fix every enum,
absent value, length, contextual mapping, and canonical vector. Generic wrappers
still require explicit acceptance rules and bounds.

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
| Fresh SAR reachability | Five challenge exchanges; one SAR signature verification per Boomlet |
| Recovery ballot | Up to one RECOVER, PREPARE, and COMMIT signature per peer, plus recovery-certificate verification |
| DIGGING continuation | Up to five fresh padded Pings and SAR exchanges, plus unresolved placeholder replay |
| Pre-DIGGING restart | Fresh transaction reviews, approvals, and commits |

Each padded Ping has two Boomlet signatures. Certificate verification, hashing,
encryption, channel operations, interface traffic, and durable writes add further
cost. Bound and measure complete workloads, maximum package sizes, journal bytes,
memory, latency, and write endurance on the intended hardware.

## 11. Companion sequence diagrams

Arrows show logical authenticated messages. Niso relays are abbreviated where
they do not affect the ordering being illustrated. A grouped peer lifeline denotes
independent operations by the named peers, with five distinct signatures and
local prerequisite checks wherever a five-peer collection is required. Diagram
references abbreviate the common exchange defined in Sections 4 through 6.

| Diagram | Coverage |
| --- | --- |
| [01_setup_changes.puml](01_setup_changes.puml) | Roster review, genesis binding, initial registration, SAR finalization, and backup additions |
| [02_common_switch.puml](02_common_switch.puml) | Review, freeze, candidate preparation, fresh SAR probe, PREPARE, COMMIT, and head installation |
| [03_setup_failover.puml](03_setup_failover.puml) | Interrupted setup checkpoints and an idle completed setup |
| [04_predigging_failover.puml](04_predigging_failover.puml) | Restart before any mystery initialization and selection of preservation for mixed states |
| [05_mixed_digging_failover.puml](05_mixed_digging_failover.puml) | Exact commit handoff to lagging peers while initialized peers retain their delay |
| [06_digging_failover.puml](06_digging_failover.puml) | Partial Pong delivery, outstanding placeholders, recovery Pings, spacing, and reached evidence |
| [07_decision_recovery.puml](07_decision_recovery.puml) | Cancellation, higher promises, certificate selection, and candidate failure during a decision |
| [08_signing_and_broadcast_failover.puml](08_signing_and_broadcast_failover.puml) | Ready-to-sign, live nonce handling, retained fragments, aggregation, and broadcast |

## 12. Validation and adoption

The bounded decision checker is run from the repository root with
`python3 scripts/check_wt_switch_decision.py`. Its three-ballot abstraction with
one honest peer and four adversarial cosigners explores 127 states and 126
transitions without conflicting final certificates. All 305 five-peer partial
prepare, certificate-learning, commit, and installation cases complete after
candidate loss. Removing retained-certificate reporting or permitting old-ballot
COMMIT produces conflicting certificates. Malformed proofs and substituted own
reports are rejected.

These checks cover the decision mechanism under durable-state assumptions.
Adoption additionally requires full integration checks for setup checkpoints,
withdrawn intents, concurrent attempts, partial activation, repeated WT reuse,
mixed withdrawal phases, pending duress challenges, placeholder equivalence,
inherited spacing, signing sessions, and restored-device revocation. Concrete
historical-age exceptions, fragment receipts, replay retention, wire bounds,
and hardware measurements must be completed together with independent protocol
and cryptographic review.

The underlying prepare, commit, and recovery pattern is informed by
[Castro and Liskov's authenticated agreement construction](https://static.usenix.org/publications/library/proceedings/osdi99/full_papers/castro/castro_html/node4.html).
The five-of-five certificate rule and its availability assumptions are specific
to this proposal. MuSig2 nonce and session requirements follow
[BIP 327](https://bips.dev/327/).
