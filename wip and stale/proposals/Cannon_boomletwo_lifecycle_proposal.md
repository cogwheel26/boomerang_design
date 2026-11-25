# Boomletwo lifecycle proposal

| Item | Value |
| --- | --- |
| Status | Draft, not adopted or verified |
| Phase 1 priority | 3 |
| Baseline | Current working-tree [`SPEC.md`](../../spec/SPEC.md), Sections 7.1, 13.10, and 18.5 |
| Related gaps | DG-04, DG-30, DG-39; AR-27, AR-28, AR-80; FM-31 |

## Scope and security boundary

Boomletwo imports a normal-key-authorized, target-bound copy of long-lived
setup state and returns `BackupDone`. The copy includes Boomlet's identity
private key and MuSig2 share, but no withdrawal mystery or live signing session.
Boomletwo also retains its own identity private key.

Activation begins after the original Boomlet is unavailable. Boomletwo performs
an independent duress check through ST and issues a key replacement certificate
using both private keys. Each recipient records Boomletwo's key as that peer's
accepted identity for future protocol actions. The setup ID, descriptor, peer
position and MuSig2 share remain fixed.

The attacker may control Niso and transport, hide newer state and emitted
outputs, replay receipts, substitute targets, and interrupt writes or messages.
Trusted device code, protected storage, and setup-time Iso and ST remain
assumptions. Recovery of an interrupted withdrawal and earlier rescue duties
uses the [checkpoint proposal](wt_failover/boomlet_rollover.md) and remains
separate from the activation duress check.

## Proposed lifecycle

Use `EMPTY`, `BACKUP_INACTIVE`, `ACTIVATING`, and `ACTIVE` as candidate
Boomletwo states, separate from withdrawal phases. Each recipient retains a
durable accepted identity for each setup peer and the certificate that changed it.

### Import

Keep each device's management identity separate from the copied logical peer
identity. Bind the encrypted transfer to the setup, source, designated target,
and attempt, with normal-key authorization and trusted-device review. Reserve
the target before export. Commit inactive import and the original `BackupDone`
receipt together; exact retries return that receipt. An ambiguous import keeps
the backup slot occupied until resolved.

### Key replacement certificate

The replacement message contains the two identity public keys:

```text
BoomletIdentityReplacement {
  boomlet_identity_pubkey,
  boomletwo_identity_pubkey
}

replacement := BoomletIdentityReplacement {
  boomlet_identity_pubkey: imported_boomlet_identity_pubkey,
  boomletwo_identity_pubkey: own_identity_pubkey
}
authorized_replacement := sign_message(
  imported_boomlet_identity_private_key,
  "Boomerang/boomletwo/key_replacement",
  (setup_instance_id, replacement)
)
replacement_certificate := sign_message(
  own_identity_private_key,
  "Boomerang/boomletwo/key_acceptance",
  authorized_replacement
)
```

Both signatures are produced by Boomletwo. The outer signature covers the
complete inner signed message. Each signature uses the selected protocol
version through `sign_message`; the inner signed tuple binds the setup.
Boomletwo takes both keys from protected state and signs only its imported
source identity and its own designated backup identity.

### Activation

1. Boomletwo enters `ACTIVATING` and durably saves a fresh activation query
   nonce and the exact `authorized_replacement` before query output. ST verifies
   the imported identity's authorization of the proposed pair and authenticates Boomletwo's query.
   ST presents the setup and replacement operation for user review.
2. Boomletwo independently runs the SPEC Section 16.2 duress check through ST
   against its stored consent set. ST displays the stored consent counter on
   this first activation query under ADR 0010. Boomletwo durably consumes the
   answer and combines its saved `under_duress` flag with the mismatch result
   using OR. A valid answer follows the same activation flow for either result.
3. Boomletwo creates and retains an encrypted SAR placeholder. Its context
   binds the activation operation, setup, both identity keys and query nonce.
   Use the imported Boomlet identity for this SAR exchange and the setup-bound
   SAR. Safe and duress cases use the same routing, fixed acknowledgment delay,
   retry policy and externally visible results under SPEC Sections 16.4–16.6.
4. Boomletwo verifies the SAR acknowledgment for the exact saved placeholder.
   It creates the outer signature and atomically commits `ACTIVE`, the complete
   replacement certificate and the activation receipt before releasing the
   certificate. Restart and exact retries recover the committed output.
5. Niso distributes the certificate to the other peers and the paired ST, WT
   and SAR. Each recipient returns its saved result for an exact retained
   certificate before applying new-certificate checks. For a new certificate,
   verify both domains, signatures, setup binding and key fields. The inner
   signer must equal that peer's currently accepted key; the outer signer must
   equal the replacement's Boomletwo key.
6. Each recipient atomically stores the new accepted identity and exact
   certificate before acknowledging or processing a subsequent action. It
   accepts future protocol actions for that peer only under Boomletwo's key.
   Conflicting or reversed replacements are rejected.

An activation query authenticates under a separate operation from the final
certificate. An inner authorization or query alone cannot change a recipient's
accepted identity. The inactive source-key restriction in SPEC Section 16.7
gains only the specific replacement signature and activation SAR exchange
defined here; host-supplied arbitrary source-key operations remain forbidden.

Keep original setup records and historical signatures as evidence. Resolve the
accepted identity through the local peer mapping when authorizing new actions,
and derive subsequent channels from the replacement identity. Historical
evidence is checked under its recorded key and context. SAR retains existing
rescue account identifiers and replay records across the identity update.

Certificate delivery may leave recipients waiting for the same saved
certificate. Their accepted identities survive restart. Activation authorizes
the replacement identity; resuming a withdrawal still requires authenticated
phase evidence, preserved duties and fresh signing sessions under the checkpoint
proposal. A fresh activation answer cannot establish that earlier rescue duties
were discharged.

### Backup replacement

The procedure covers the one designated setup backup. Replenishing or replacing
that backup needs a separate eligibility and authorization procedure. Retain an
ambiguous import's reservation and all issued certificates until that procedure
or a fresh setup resolves the target's eligibility.

## Security requirements

These conditions apply to any selected mechanism. All are proposed and pending
validation.

### BW-SR-01 Accepted peer identity

Each recipient stores one accepted identity key per peer and setup. After
committing the replacement certificate, it accepts future state-advancing
protocol actions for that peer only under Boomletwo's key. Restart and replay
cannot restore the predecessor mapping.

### BW-SR-02 Inactive backup confinement

Import and `BackupDone` establish an inactive backup. Activation requires the
trusted ST interaction, independent duress check, exact SAR acknowledgment and
durable target decision. Only the complete replacement certificate changes a
recipient's accepted identity.

### BW-SR-03 Bound lifecycle decisions

Authenticate the operation, profile, setup and both keys. The outer signature
covers the complete inner signed message. Bind the duress exchange to its saved
query nonce and exact placeholder. Reject wrong context, target substitution,
conflicting replacements and delayed input for another activation.

### BW-SR-04 Atomic import and exact recovery

Reserve the target before export and commit inactive import with its
original receipt. Exact retries recover that result without another grant;
lost replies, partial writes, and ambiguous state cannot free the slot or make
a second target eligible.

### BW-SR-05 Current state and obligations

For withdrawal recovery, carry forward replay floors, consent restrictions,
withdrawal identity, commitments, pending SAR duties, signing records and
applicable WT decisions. A valid old checkpoint cannot prove later duties
absent. Recover hidden later state or block withdrawal resumption; later consent
cannot clear pending rescue delivery.

### BW-SR-06 Withdrawal and signing safety

Preserve transaction review, unanimous approval, SAR acknowledgment, digging,
and signing gates. Preserve the checkpoint proposal's conservative delay floor
and one saved recovery draw. Do not credit old traffic, redraw on retry, reuse
a MuSig2 nonce, erase emitted fragments or restart uncertain signing as unused.
Resume an interrupted withdrawal only after its required state and evidence
have been recovered.

### BW-SR-07 Consent continuity

Preserve consent state and pending obligations under
[SPEC Section 16.7](../../spec/SPEC.md#167-consent-rotation).
A stale backup cannot restore an invalidated answer; required private enrollment
and trusted ST confirmation precede withdrawal. The consent set alone cannot
authorize lifecycle changes, and prompts or receipts cannot reveal or test it.
Any accepted exposure needs an explicit reduced claim.

### BW-SR-08 Confidentiality and duress observability

Transfer private material only in authenticated, target-bound encrypted
envelopes; keep keys, nonces, mysteries, consent answers, and rescue plaintext
out of public records and diagnostics. Preserve SPEC Sections 16.4–16.6 on
placeholder delivery, exact acknowledgment, deadlines, retries, and observable
errors. Lifecycle handling cannot disclose classification or cancel committed
rescue; visible maintenance activity is outside that protocol guarantee.

### BW-SR-09 Durable identity replacement

Commit Boomletwo's activation and exact certificate before output. Recipients
commit the accepted key and certificate together before acknowledgment or new
actions. Exact retries recover the recorded result without reinstalling private
state or clearing replay records.

### BW-SR-10 Activation dependencies

Activation uses Boomletwo's imported keys, enrolled ST, setup-bound SAR and
certificate delivery to recipients. Missing prerequisites may stall the saved
attempt. Certificate issuance and recipient installation use durable local
state and exact recovery outputs.

### BW-SR-11 Backup replacement

At most one inactive backup may remain eligible. Exclude the old target before
replacement, including delayed imports, issued receipts, and restored state.
An unresolved import occupies its slot. Replenishment binds the new source,
target, and predecessor; otherwise block or specify setup migration.

### BW-SR-12 Reviewable authorization

Setup normal-key authorization binds the designated backup. Activation requires
trusted ST review of the exact setup and key pair and an independent duress
check. Specify who initiates, cancels and resumes after credential loss.
User interaction preserves withdrawal and rescue duties.

### BW-SR-13 Resource and storage bounds

Set byte, nesting, proof, retry, and persistent-storage limits; reserve journal
and receipt capacity before irreversible steps. Invalid input, exact retries,
capacity exhaustion, interrupted writes, and counter overflow cannot change
authority or evict required evidence. Exact retries cannot consume new attempts
or cause unbounded writes. Measure endurance and availability limits.

### BW-SR-14 Device identity and compatibility

Keep physical management identity distinct from the copied peer key and bind
it through import; a copied-key signature alone cannot identify a device.
Reject unsupported profiles. Counters need protected state, not only wire fields.

### BW-SR-15 Emitted outputs and migration

Account for signatures, fragments, commitments, and receipts emitted before
activation, including concealed outputs. If migrating, bind review to the new
descriptor and define spending authority, confirmation, competing-spend,
reorganization, and later-deposit rules. Track funds still reachable through
the old setup.

### BW-SR-16 Cancellation and completion

Define durable outcomes and safe cancellation at every interruption point.
Retain accepted duress and outstanding SAR delivery when an attempt is
interrupted. A committed certificate remains retrievable and is never cancelled
by a lost acknowledgment. Name the services, storage, delivery and user actions
needed for completion and demonstrate availability under those assumptions.

## Required validation evidence

All cases are pending. Results must pin protocol and implementation or model
revisions, assumptions, explored bounds, and remaining limits. WT checkpoint
experiments do not validate this lifecycle. Model durable device state,
in-flight evidence, stale snapshots, and adversarial delivery; test hardware
rollback and storage assumptions separately.

| Case | Exercise and required result | Requirements |
| --- | --- | --- |
| BW-T01 | Activate from Boomletwo's stored backup, distribute the certificate and verify each recipient accepts future actions only under the replacement key. | 01, 02, 09, 10 |
| BW-T02 | Substitute context fields and replay approvals; reject unauthorized transitions. | 03, 12, 14 |
| BW-T03 | Interrupt each import, activation and recipient-installation write or reply; recover the committed result or block. | 01, 04, 09, 16 |
| BW-T04 | Lose `BackupDone`, retry, conflict imports, and race targets; keep one reservation and successor. | 03, 04, 11 |
| BW-T05 | Hide later duress, WT, consent, or signing state behind a valid old snapshot; recover duties or block. | 05, 07, 15 |
| BW-T06 | Restore a recipient's predecessor mapping or replay a certificate after replacement; retain the committed accepted key and exact result. | 01, 09, 11, 14 |
| BW-T07 | Try historical-pong credit, redraws, nonce reuse, transaction substitution, and fragment loss; preserve gates. | 05, 06, 15 |
| BW-T08 | Try stale consent and target substitution; inspect records for secret disclosure. | 07, 08, 12, 14 |
| BW-T09 | Compare safe and duress activation under retries, capacity pressure and failures; preserve sticky duress, exact SAR discharge and acknowledgment observations. | 02, 05, 08, 13 |
| BW-T10 | Exceed input, retry, storage, and counter bounds; preserve authority and required evidence, and measure costs. | 04, 13 |
| BW-T11 | Withhold receipt or acknowledgment and attempt cancellation; preserve authority and conditional completion. | 04, 09, 16 |
| BW-T12 | Replenish and conceal an old signed spend during migration; enforce eligibility and old-setup exposure. | 11, 14, 15 |

The bounded activation model in the checkpoint proposal covers abstract duress,
SAR and recipient-installation ordering. The validation cases above additionally
require exact wire, device, import and withdrawal-recovery evidence.

An unmet requirement blocks adoption or requires an explicit revision of the
security claim.

## Decisions and integration

- Complete canonical certificate and activation SAR encodings, signature domains,
  bounds, protected lifecycle writes and exact retry outputs.
- Specify ST authentication and review, recipient installation, channel changes
  and distribution of the saved certificate.
- Finish interrupted-withdrawal recovery, earlier-duty recovery and signing
  disposition with the checkpoint proposal.
- Define backup replenishment and cancellation before certificate commitment.

Adoption requires updates to SPEC Sections 7, 9–10, 12–13, 15–18, and 21–22;
wire schemas and vectors; setup and withdrawal contracts and source diagrams;
DESIGN and GLOSSARY; DG-04/DG-39 entries; and an ADR for authority and
compatibility decisions. Validation of the activation procedure and recipient
installation remains pending.
