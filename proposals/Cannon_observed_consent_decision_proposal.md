# Observed-consent decision proposal

| Item | Value |
| --- | --- |
| Status | Draft, not adopted |
| Phase 1 priority | 2 |
| Normative baseline | [`SPEC.md`](../spec/SPEC.md) at `ed91233a4216be0c96f8f8d081276b7c94a39751` |
| Related gaps | DG-38, AR-35, AR-79, FM-30, R-12, R-21 |

## Problem and scope

The five-country `duress_consent_set` is copied from Boomlet to Boomletwo and
remains safe for the setup's lifetime. Fresh permutations and nonces prevent
transcript replay, but an attacker who learns a safe selection can recognize or
dictate it later. Consent replacement and backup activation remain unresolved.

The decision is whether to replace the setup, change the protocol, or explicitly
accept exposure. Observation includes recording, dictated input, and device
extraction. It does not grant signing keys, suppress other peers' signals, or
cancel rescue already triggered. Recovery protects later ceremonies; it cannot
undo disclosure during a coerced interaction.

## Required properties

For fixed-set recovery, success requires these properties. Quarantine begins on
known or suspected disclosure; its enforcement on offline devices and any
restricted rollover exception must be defined.

| ID | Property |
| --- | --- |
| OC-SR-01 | No eligible device classifies an observed set as safe after recovery. |
| OC-SR-02 | Only one set is safe per active Boomlet; no overlap preserves the exposed answer. |
| OC-SR-03 | Crashes, retries, and rollback cannot restore invalidated authority. Ambiguity blocks ordinary withdrawal. |
| OC-SR-04 | Backup activation cannot restore exposed consent or bypass required enrollment. |
| OC-SR-05 | Consent maintenance cannot grant signing authority or weaken the one-active-Boomlet invariant. |
| OC-SR-06 | Fixed-set enrollment uses trusted ST, two fresh nonce-bound confirmations, and a private environment. |
| OC-SR-07 | Transcripts and public records provide no offline test for guessing the secret. |
| OC-SR-08 | In-place maintenance occurs outside withdrawal and preserves SAR observability rules. |
| OC-SR-09 | A trusted interface identifies the current device, ceremony, and consent state. |
| OC-SR-10 | Device loss, stale backups, interrupted maintenance, and unavailable authorities have recovery actions. |

Broader designs must specify replacements for the fixed-set and unchanged-wire
requirements. Option 11 explicitly trades concealment for independent review.
Every option retains the signing-authority invariant.

## Common security limits

- Restore compromised devices and assess exposed keys before recovery. A new set
  cannot repair a device that leaks answers or ignores invalidation.
- The exposed set cannot be the sole maintenance credential. Authentication and
  two matching confirmations establish neither privacy nor freedom from coercion
  [R3]; the device cannot verify those environmental assumptions.
- After rotation, an old but valid set must follow the ordinary duress path.
  A distinctive rejection or retry would disclose classification.
- Offline backups need enforced retirement, updates, or fresh activation authority.
  Signed old records do not prove freshness. Counter storage must resist rollback.
- Exclude known exposed sets using protected history. Lost history limits proof
  of lifetime non-reuse. Public hashes permit guessing; properly hiding
  commitments need not [R2]. Neither commitments nor equality proofs establish
  durable invalidation.
- Preserve pending rescue during maintenance. Bound retries and writes to limit
  denial of service. Protocol-controlled timing and errors must conceal
  classification, although human maintenance activity may reveal suspicion.
- Scheduled rotation limits unnoticed exposure only when later enrollment is
  private. Continuous disclosure of each replacement defeats fixed-set rotation.

## Option 1. Full setup replacement

Quarantine, enroll a fresh setup, move funds to its descriptor, and retire the old
consent-bearing devices. Permit only a restricted rollover bound to the verified
new descriptor and required peer approvals; arbitrary maintenance spending would
create a withdrawal bypass.

### Pros

- Avoids paired consent epochs and reuses setup enrollment.
- Confirmed rollover removes transferred funds from old spending paths and can
  replace other exposed keys.

### Cons

- Requires peers, fees, and confirmations while exposure persists. Competing
  spends, outstanding signatures, reorganizations, and fallback constrain timing.
- Still needs durable quarantine and device retirement. Fresh setup creation
  alone cannot recover funds without existing spending authority.
- Reusing exposed sets or compromised devices defeats recovery. Stop issuing old
  deposit addresses and define handling of later deposits to them.

## Option 2. Immutable set with accepted exposure

Continue accepting the same set after disclosure; replacement remains voluntary.

### Pros

- Preserves availability without consent-update state or authority.
- Retains signing checks, peer approvals, delays, and other peers' duress signals.

### Cons

- A coercer controlling input can force the affected user's checks to remain safe.
- Nonces and shielding cannot restore the disclosed secret. This fails OC-SR-01
  and requires an explicit reduction in the security claim.

## Option 3. Paired rotation

Transfer a fresh set to the inactive backup and durably commit the same epoch on
both devices. Bind updates and receipts to setup, identities, epoch, and
transition. An uncertain participant blocks until decision evidence or recovery
is available. Two-phase commit can preserve safety while blocking [R1]; a witness
is a recovery and availability choice, not universally required for safety.

### Pros

- Preserves one memorized answer, the descriptor, and service registrations.
- A completed update leaves backup consent current, subject to activation checks.

### Cons

- Requires both devices and stores the secret twice, increasing correlated exposure.
- Partial commits, rollback, and missing evidence can block recovery. A witness
  adds outage, privacy, and equivocation risks.
- Aborting after disclosure must return to quarantine, never the exposed answer.
  Updating consent must not activate signing authority.

## Option 4. Independent device consent state

### Variant 4A. Same set enrolled separately

Enter one fresh set independently on both devices. Authenticated private equality
checking can detect mismatch without publishing a guessable hash [R2].

#### Pros

- Avoids transmitting the set between devices while retaining one memorized answer.

#### Cons

- Repeats exposure and error opportunities while retaining the coordination problem.
- Equality does not prove durable commit. A partial update must exclude the stale
  device; accepting both answers to mask mismatch violates OC-SR-02.

### Variant 4B. Distinct pre-enrolled sets

Memorize one independent set per device and rotate each exposed set before that
device next activates.

#### Pros

- Disclosure of one independently chosen set need not expose the other.
- Active rotation need not update backup consent; backup enrollment is already done.

#### Cons

- Two sets, including a rarely used one, increase confusion and false duress.
- Related sets and common ST compromise weaken separation. Backup eligibility
  still requires compromise tracking; wrong-device hints must not reveal answers.

### Variant 4C. Enrollment on backup activation

Store `CONSENT_REENROLL_REQUIRED` in the backup. After excluding the old signing
authority, require private ST enrollment before withdrawal. Rotate active consent
locally through durable quarantine, confirmation, and commit.

#### Pros

- Removes shared consent and its synchronization; the user remembers one set.
- Backup activation cannot restore a copied exposed answer.

#### Cons

- Recovery requires private enrollment when the user may be rushed or coerced.
  The device cannot detect an attacker dictating the replacement.
- Requires enforceable revocation of a missing active device. Lost history limits
  non-reuse guarantees; enrollment delays backup readiness.

### Variant 4D. Retire the backup before local rotation

Erase a reachable trustworthy backup or revoke it through every future activation
path. Rotate locally, then provision a replacement backup.

#### Pros

- Avoids paired commit and supports migration from copied consent state.
- Temporarily limits consent storage to the active device.

#### Cons

- Losing the remaining device may leave only fallback spending paths.
- Declaring a missing device retired is insufficient. Erasure cannot retract
  extracted secrets; replacement must not revive old signing authority.

## Option 5. Derived sets with a witnessed epoch

Both devices derive consent from a protected high-entropy root and a committed
epoch. A witness records the current epoch; the user privately learns and confirms
each set before commitment.

### Pros

- Avoids transferring each replacement set to an offline backup.
- A protected pseudorandom derivation can isolate observed outputs across epochs.

### Cons

- Static-root compromise exposes all covered epochs; advancing the counter cannot
  repair it. Sampling, repeated sets, and protected history need explicit rules.
- Witness records can be stale or conflicting. Replication needs a fault model
  and quorum protocol, with outage and metadata costs.
- User confirmation, commitment, and backup activation still need crash recovery.

## Option 6. Challenge-dependent responses

Replace the reusable answer with a ceremony-specific response. One concrete
candidate privately pre-enrolls independent answers, allocates one durably before
each ceremony, repeats it only for that ceremony's retries, and never reuses a
spent entry. Other candidates compute responses from a protected secret.

### Pros

- Observing a spent answer need not enable a later ceremony, even without detection.
- Reduces reliance on discretionary rotation after disclosure.

### Cons

- Public challenge-response pairs may reveal a low-entropy root through offline
  guessing. Fresh nonces alone do not prevent this.
- An authenticator that automatically returns safe gives the coercer that path;
  the user still needs a concealed duress choice.
- Consumption, exhaustion, backup rollback, and replenishment add state. Stored
  sequences can be seized; memorization and calculation increase errors.
- Exposure remains within the ceremony while its allocated answer stays valid.

## Option 7. Witnessed encrypted recovery

Enroll independent fresh sets and store randomized, target-bound recovery
envelopes externally. A witness binds the committed epoch to the exact envelope;
Boomletwo imports only the current one during authorized recovery.

### Pros

- Permits rotation with an offline backup without one permanent derivation root.
- A ciphertext digest can identify the envelope without exposing a plaintext
  guessing test; storage and epoch authority can be separate.

### Cons

- A compromised recipient key exposes captured envelopes, including future ones
  until that recipient is revoked or replaced.
- Storage deletion, stale records, and equivocation threaten recovery. Encryption
  proves neither freshness nor availability.
- Confirmation, storage, witness commitment, and activation require coordinated
  recovery, service availability, and additional key management.

## Option 8. Consent authority in ST

Move persistent consent and comparison into ST; neither Boomlet stores the set.
ST returns a ceremony-bound receipt and SAR-encrypted classification with uniform
public behavior. Boomlet requires acknowledgment of that exact payload. Keeping
the existing placeholder format gives ST `doxing_key_for_sar`; otherwise redesign
rescue release. Replacement STs reenroll instead of importing stale consent.

### Pros

- One consent authority serves both devices, removing their consent synchronization.
- Rotation can remain local and preserve the descriptor.

### Cons

- Concentrates durable consent and rescue authority in ST. Compromise can force
  safe classification; receipts prove origin, not honest behavior.
- Moves backup, rollback, and revocation problems into ST. Old identities and
  pending receipts need cutover rules.
- Changes provisioning, placeholder authentication, and SAR trust under OC-SR-08.

## Option 9. Online consent verifier

ST submits encrypted, authenticated responses to an authoritative service on each
check. The verifier binds its consent epoch and verdict to the ceremony, producing
a uniform receipt and SAR-confidential classification. Boomlet requires SAR's
acknowledgment; backups cannot substitute cached consent.

### Pros

- Rotation updates one record and reaches offline backups at their next required
  check without distributing the new set to them.
- Protected history can survive local-device loss.

### Cons

- Adds service dependence, censorship, classification privacy, and database risks.
  A compromised verifier can suppress duress; replication needs explicit trust bounds.
- Wrong valid sets must signal duress, not authentication failure. Ordinary OTP
  success receipts expose classification and can permit relay [R3].
- Must define rescue authority and pending-verdict cutover. Revocation cannot undo
  completed signing or a delivered rescue signal.

## Option 10. Private randomized cues

Privately show the user a fresh safe button position for each round. All fixed
rounds must match for safe; any valid mismatch means duress, with uniform public
behavior. Bind and erase cue state. This implements Option 6 through a private
visual or tactile channel rather than a memorized sequence.

### Pros

- Removes the reusable set and its backup synchronization.
- Recording public inputs need not reveal classification or future private cues.

### Cons

- Assumes the coercer cannot observe, demand, or take over the private cue channel.
  Cameras, physical leakage, and forced demonstrations challenge that assumption.
- Small choice spaces permit safe guesses. More independent rounds reduce guessing
  but increase user error; retries and independence require justification.
- Changes hardware and accessibility needs. Motor behavior may reveal deviation;
  observation studies alone do not establish active-coercion resistance [R4].

## Option 11. Mandatory independent rescue review

Every withdrawal opens a durable SAR case before progress. Independent guardians
review intent; signing requires clearance, while unresolved cases escalate under
a deadline policy. The exposed set or local user alone cannot cancel review.
Define clearance and escalation thresholds, rescue-data access, and enforcement
by both devices, including fallback limits.

### Pros

- A safe local answer cannot suppress all review; rescue consideration can begin
  without a covert signal.
- Distributes judgment beyond the locally coerced user.

### Cons

- Requires available, honest, independently situated guardians. Collusion or
  coerced clearance defeats review.
- Routine review exposes more information; outages can cause false escalation.
  Visible refusal may alert the coercer and increase physical danger.
- Replaces SAR release and concealment rules. A veto does not establish timely
  rescue; guardian replacement and fallback remain attack paths.

## Proposed disposition

Keep Option 1 as the conservative candidate, conditional on safe restricted
rollover. Option 2 is explicit acceptance of reduced protection.

Compare Variant 4C with Option 8 for local rotation; consider Option 9 if mandatory
online verification is acceptable. Options 3, 5, and 7 serve pre-enrolled backup
readiness; Variant 4D supports migration when temporary backup loss is acceptable.
Options 6 and 10 target unnoticed observation. Option 11 adds independent response
at the cost of some concealment. These are candidates, not verified guarantees.

## Validation and adoption

- Exercise every durable transition under message loss, crash, replay, rollback,
  device loss, stale backup activation, and attempted duplicate authority.
- Test unauthorized or coerced maintenance, exposed-set reuse, stolen keys,
  guessing from transcripts, exhaustion, and false-safe or false-duress rates.
  Preserve queued rescue; old valid sets must not produce distinctive errors.
- For rollover, test destination substitution, competing signatures, reorganization,
  peer refusal, fees, residual deposits, and every fallback boundary.
- For witnesses, ST authority, and verifiers, test stale or conflicting records,
  substituted payloads, outages, compromised authority, and pending-receipt cutover.
- For sequences and cues, test repeated observation, dictated input, physical
  leakage, retries, exhaustion, accessibility, and user error. For guardians,
  test collusion, coerced clearance, silence, false escalation, and rescue timing.

Broader changes require versioned messages, authority and observability rules,
and migration tests. Retire or revoke old devices capable of bypassing new gates;
if that cannot be enforced, roll funds over. Updating new devices alone leaves
old spending authority intact.

Adoption requires an explicit choice, documented lost properties, operator
recovery actions, and reproducible evidence. Tests cover exercised cases;
model checks establish properties only within their stated assumptions.

Update `spec/SPEC.md`, setup and withdrawal documentation, `DESIGN.md`, `README.md`,
`GLOSSARY.md`, security models, an ADR, and operator runbooks for the selected
option. Option 1 specifically requires durable quarantine, restricted rollover,
active-withdrawal handling, rescue preservation, device retirement, and evidence
that rollover meets its timing bounds. Change PlantUML only for adopted protocol
changes; do not regenerate SVGs.

## Review basis

Protocol reasoning uses SPEC Sections 13.3, 16.1–16.6, 18.5, and 19.1. External
sources support the cited technical points, not the proposed designs as a whole.

- [R1] Gray and Lamport, *Consensus on Transaction Commit* (2006).
  DOI `10.1145/1132863.1132867`.
- [R2] Metere and Dong, *Automated Cryptographic Analysis of the Pedersen
  Commitment Scheme* (2017). DOI `10.1007/978-3-319-65127-9_22`.
- [R3] NIST SP 800-63B-4, Sections 3.1.3, 3.2.5, and 3.2.8.
  DOI `10.6028/NIST.SP.800-63B-4`.
- [R4] Bošnjak and Brumen, *Shoulder surfing: From an experimental study to a
  comparative framework* (2019). DOI `10.1016/j.ijhcs.2019.04.003`.
