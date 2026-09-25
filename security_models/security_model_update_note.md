# Security model update note

## Dynamic rescue-data lifecycle (2026-09-22)

Independent reassessment is pending. Use the current [SPEC](../spec/SPEC.md)
and [adopted lifecycle proposal](../proposals/Cannon_dynamic_rescue_data_lifecycle_proposal.md)
as design inputs. The existing security model still describes selection of one
current dynamic update in several places.

### Changed controls and remaining exposure

- SPEC Sections 10 and 13.1 define a protected first registration, an account
  upload credential, authenticated append, exact signed receipts, idempotent
  retries, and rejection of conflicting bytes under one upload identity.
  Accepted uploads remain in history; Phone has no erasure authority.
- `SetupPhoneSarMessage2` carries payment receipts, identifier, static envelope,
  and the key and first-upload tuple together; `SetupSarPhoneMessage2` returns
  the signed upload receipt. Reassess registration binding, partial failures,
  and complete-request retries against the atomic commit of the static
  envelope, profile, key, first upload, and receipt.
- Each accepted upload remains in history. Reassess the old-update replacement
  branch of T-DATA-02 in light of that rule. Receipt signatures prove acceptance
  of individual encrypted uploads, not complete retention or truthful payloads.
- Per-device upload sequence numbers expose uploader-assigned first-submission
  order despite delayed delivery. They do not establish send time, cross-device
  order, or completeness. Random upload IDs remain the unique identity, so a
  credential holder cannot preempt an upload solely by predicting its sequence
  number. Reassess gaps, counter reuse, duplicate-number ambiguity, and
  out-of-order acceptance independently.
- Any holder of the password-derived account credential can append under any
  device ID. Old Phones retain that authority. The credential gives an attacker
  another offline password-guess verifier if SAR state is exposed.
- A compromised Phone can append misleading observations or stop uploading.
  A malicious or failed SAR can hide or lose accepted history. The rescue
  application must interpret relevance and freshness; authentication cannot
  establish either.
- A credential holder can submit enough valid uploads to exhaust new-upload
  capacity. Capacity controls may reject new entries but must retain accepted
  history and allow exact receipt retrieval.
- Protected enrollment, storage capacity, crash recovery, and
  history access after duress need deployment evidence. The design assumes SAR
  preserves accepted history through supported storage failures. Reassess
  incomplete restoration, shared-resource contention, and protocol-visible
  timing or failure channels when rescue processing overlaps the held
  acknowledgment.

### Review targets

| File | Entries to reassess |
| --- | --- |
| [Risk register](README.md) | Assets, SAR registration phase, H-03, R-06, R-07, R-22, R-26, DG-11, DG-40, and the related validation action. Revisit risk scores and statuses after assessing the new controls and remaining exposure. |
| [Architecture](architecture.md) | Phone and SAR boundaries, registration and upload flows, SAR store, data classification, and the `DynamicDoxingData.captured_at` claim. |
| [Assumptions](assumption_register.md) | AR-45, AR-59, AR-67, AR-81, and FM-32. Include credential establishment, concurrent append, lost replies, replacement Phones, crash and restoration assumptions, and payload interpretation in the model scope. |
| [Attack trees](attack_trees.md) | The dynamic-data branch near P5 and the Phone and SAR compromise paths. Check false uploads, stopped uploads, hidden history, and incomplete restoration. |
| [Audit mappings](audit_mappings.md) | T-DATA-02, T-CRYPTO-03, T-PHONE-01, T-INFO-01, T-INFO-08, T-DURESS-04, service-capacity threats, and related control rows. Existing suggestions to rotate Phone credentials need review because the adopted account credential cannot be replaced within the account. |

No gap or threat is resolved by this handoff. The reviewer should decide which
claims are mitigated by the protocol, which depend on implementation evidence,
and which remain operational risks.
