# Dynamic rescue-data lifecycle proposal

| Item | Value |
| --- | --- |
| Status | Adopted into the design specification, 2026-09-18; deployment evidence pending |
| Phase 1 priority | 1 |
| Proposal baseline | [`SPEC.md`](../spec/SPEC.md) at `8ad77efabe03385d60733827fe55b3f988519c65` |
| Related gaps | DG-11, DG-40 |
| Normative integration | Current [`SPEC.md`](../spec/SPEC.md) |

## Integration change map

Recorded 2026-09-18 before applying the integration. The user requested adoption
of this proposal, a running changelog, and an incremental Phase 1 report.

| File | Places to change | Intended result |
| --- | --- | --- |
| `spec/SPEC.md` | Sections 7.5, 8.3, 9.4, 9.6, 10, 13.1, 16.4, 18.1–18.4, 19.4, 19.9, 20–22 | Account credential and profile state; device KDF; authenticated append; exact receipts; bounded opaque payloads; registration, replacement, retry, recovery, and complete-history rescue access. |
| `spec/wire_catalog.json`, `spec/wire_catalog.txt` | Schema registry, signature domains, encryption contexts, registration tuple, generated layouts | Reserve ID 11; assign IDs 30 and 31; register exact types and regenerate the text catalog. |
| `spec/dynamic_rescue_vectors.json`, `scripts/check_dynamic_rescue.py` | New focused vectors and executable checks | Reproducible cryptographic bytes and lifecycle scenarios, with evidence boundaries recorded. |
| `setup/setup_development_contracts.md`, `setup/setup_no_prose_guards.md`, `setup/README.md` | SAR registration, stored objects, receipt verification, retry | Protected account registration and signed first-upload receipt. |
| `no_prose_crypto_contracts.md`, `setup/*.puml`, `withdrawal/*.puml`, `duress_protection/*.puml` | SAR upload and rescue-data retrieval fragments | Device-key encryption and asynchronous access to all retained uploads; source edits only. |
| `DESIGN.md`, `GLOSSARY.md`, `withdrawal/README.md`, `duress_protection/README.md` | Rescue data, registration, replacement, activation | Terminology and explanatory behavior consistent with the specification. |
| `security_models/security_model_update_note.md` | DG-11, DG-40, T-DATA-02, related risks and assumptions | Hand off affected security-model entries for independent reassessment. |
| `outside/Cannon_roadmap.md`, `outside/Cannon_phase_1_report.md`, `CHANGELOG.md` | Dynamic-data milestone, progress, decisions, evidence, chronological entries | Adopt history retention and record progress and remaining gates as work proceeds. |
| This proposal | Status, current-status baseline, roadmap divergence, object limits, integration checklist | Record adoption and exact implementation choices without claiming unrun deployment tests. |

The independent review should also revisit the rescue-data attack-tree branch
and SAR data-flow labels. The [security review note](../security_models/security_model_update_note.md)
lists the affected entries.

The catalog integration also updates `scripts/generate_wire_catalog.py` to
validate reserved schema IDs and report the registered dynamic exchange types.

## Current status

The specification defines authenticated append, account and device history
identity, exact signed receipts, protected first registration, replacement,
non-erasure, retry, conflict rejection, and recovery requirements. Schema ID 11
is reserved; `DynamicRescueUpload` and `DynamicRescueReceipt` use IDs 30 and 31.

The [changelog](../CHANGELOG.md) records integration and validation. The
[Phase 1 report](../outside/Cannon_phase_1_report.md) records evidence and open
gates. The existing DG-40 entry awaits independent reassessment. Protected
provisioning, real storage restoration, capacity, and duress-observability
validation remain open.

## Roadmap goal

Define authenticated append, complete-history retention, exact retries,
conflict rejection, and detection of incomplete SAR restoration. Corrections
append without suppressing accepted evidence. Payload meaning and freshness
belong to the rescue application.

## Reason for divergence

The baseline milestone assumed one current record. Dynamic payloads can be a
stream, independent observations, or another collection in which late and
conflicting entries remain useful. Selecting one current record would add
payload semantics and let a malicious Phone make earlier evidence obsolete.

| Milestone objective | Proposal treatment |
| --- | --- |
| Prevent an older valid upload from replacing a newer one | Satisfied because no upload replaces another |
| Accept corrections | Satisfied by appending corrected data while retaining prior data |
| Reject rollback | Require SAR crash recovery to preserve accepted history and detect incomplete results |
| Handle duplicates and conflicts | Exact retries are idempotent; distinct uploads are retained; upload ID collisions are rejected |
| Identify one current update | Replaced by complete-history delivery to SAR implementation |
| Define version order | Unneeded because the protocol does not select a winner |
| Define expiry and Phone clock skew | Delegated with freshness and relevance to SAR implementation |

A later payload has no protocol authority to suppress an earlier one. The
protocol remains independent of payload meaning while satisfying the
milestone's non-replacement, correction, rollback, duplicate, and conflict
goals.

The adopted roadmap uses authenticated append, complete-history retention,
and rollback detection. Deployment evidence remains a completion gate.

## Adopted changes

| Area | Adopted behavior |
| --- | --- |
| Payload | Bounded bytes interpreted by SAR's rescue application |
| Storage | Retain every accepted encrypted upload |
| Identity | Identify uploads by account, device ID, and upload ID |
| Encryption | Derive a device-data key from `doxing_key_for_sar` |
| Authentication | Authenticate uploads with a separate account upload key |
| Acknowledgment | Return a signed receipt for the exact encrypted envelope |
| Registration | Extend the existing Phone/SAR setup exchange for the first device |
| Replacement | Reconstruct account upload authority and choose a fresh device ID |

The identifier derivation, static-data encryption, and Boomlet release of
`doxing_key_for_sar` remain as specified. Dynamic uploads use the existing
cryptographic primitives and canonical encoding.

## Requirements

### DRD-SR-01 Phone non-erasure

No Phone message, credential, secret, or procedure for restoring Phone
credentials can make SAR hide, delete, truncate, reset, or forget an accepted
upload. Later uploads cannot revoke or supersede earlier uploads. SAR makes
every retained upload and receipt available to its rescue application.

Retention continues while a related Boomerang setup may remain active. Later
deletion requires independent SAR authority; Phone cannot authorize it.

### DRD-SR-02 Payload agnosticism

The payload is a bounded `bytes` value. The protocol assigns no payload format,
source timestamp, ordering, freshness, or semantic validation rule. Payload
meaning cannot affect acceptance, retention, receipts, retries, or withdrawal.

### DRD-SR-03 Durable append

SAR keeps separate histories for each `(doxing_data_identifier, device_id)` and
appends each accepted authenticated upload atomically. Exact retries return
the original receipt. No accepted upload replaces another.

### DRD-SR-04 Device IDs and Phone replacement

Phone generates `device_id = random_bytes(32)` once for its history and
`upload_id = random_bytes(32)` for each new upload, using SPEC Section 9.2.
Retries retain both IDs and the complete original upload.

A replacement Phone reconstructs the account credential from the doxing
password, selected SAR, and registration protocol version, then chooses a
fresh device ID. Its first valid upload starts that device ID's history;
no additional device enrollment exchange is required.

Device IDs separate histories and encryption keys. Authorization belongs to
the account: any holder of the upload credential can submit under any device
ID, including an existing one. SAR does not attest which physical Phone sent
an upload. An upload naming one device ID does not modify entries associated
with another ID. Old Phones retain append authority, but cannot erase or
replace accepted entries.

## Objects

```text
DynamicRescueUpload {
  doxing_data_identifier: bytes32,
  device_id: bytes32,
  upload_id: bytes32,
  encrypted_payload: CbcCmacEnvelope,
  authenticator: bytes16
}

DynamicRescueReceipt {
  doxing_data_identifier: bytes32,
  device_id: bytes32,
  upload_id: bytes32,
  encrypted_payload_hash: bytes32
}
```

Receipts use the existing `SignedMessage` wrapper with content type
`DynamicRescueReceipt`. All objects follow SPEC Sections 8.2 and 8.3 for
canonical encoding, fixed-width types, and encoded-size limits. SPEC Section
8.3.1 fixes the payload ceiling at 65,536 bytes; maximum encoded sizes are
65,608 bytes for its envelope, 65,741 for an upload, and 65,777 for the
registration tuple. A receipt is 147 bytes and its signed wrapper is 301 bytes.
Both new schemas use version 1 and field IDs starting at 1 in declared order.

The bound limits per-upload work on Phone and SAR; deployment capacity and
throughput evidence remain open. Capacity rejection cannot evict accepted
history or block exact authenticated receipt retrieval.

## Cryptographic definitions

### Keys

Use `kdf_counter_cmac_aes256` from SPEC Section 9.4; output lengths are in bytes.
`PROTOCOL_VERSION` is the account's registration profile version.

```text
device_data_key = kdf_counter_cmac_aes256(
  doxing_key_for_sar,
  "Boomerang/sar_dynamic_device_data_key/v1",
  canonical_encode(device_id),
  32
)

dynamic_update_auth_key = kdf_counter_cmac_aes256(
  doxing_key_for_sar,
  "Boomerang/sar_dynamic_update_auth_key/v1",
  canonical_encode(PROTOCOL_VERSION, doxing_data_identifier),
  32
)
```

### Encrypted payload

Encrypt one canonical variable-length `bytes` value with `cbc_cmac_encrypt`
and the following keys and context:

```text
keys = derive_cbc_cmac_keys(device_data_key, "Boomerang/sar_stored_data")

context = canonical_encode(
  "Boomerang", PROTOCOL_VERSION, "sar_dynamic_data",
  doxing_data_identifier, device_id, upload_id
)
```

The shared key schedule retains `Boomerang/cbc_cmac/key_schedule/v1`.
Decryption uses `cbc_cmac_decrypt` with the same inputs. The existing fresh-IV,
full-tag, authentication-before-decryption, and rejection rules apply. Dynamic
stored data require no setup or withdrawal identifier.

### Upload authentication

```text
authenticator = aes256_cmac(
  dynamic_update_auth_key,
  canonical_encode(
    "Boomerang/sar_dynamic_upload/v1", PROTOCOL_VERSION,
    doxing_data_identifier, device_id, upload_id, encrypted_payload
  )
)
```

Use the full 16-byte result and constant-time verification. The separate upload
key lets SAR authenticate submissions before duress releases the data key.
It authorizes upload and receipt retrieval only. SAR cannot verify the inner
data-key tag before duress release; accepted undecryptable entries remain
retained, and their failures cannot hide other entries from rescue processing.

### Receipt

```text
encrypted_payload_hash = sha256(canonical_encode(encrypted_payload))

signed_receipt = sign_message(
  sar_private_key,
  "Boomerang/setup/sar_dynamic_receipt",
  receipt
)
```

Phone calls `verify_signature` with the selected SAR public key and exact
domain, then matches the account identifier, device ID, upload ID, and envelope
hash against its upload. The existing signature helper provides BIP340 signing
and protocol-version binding.

## Processing

### First-device registration

Dynamic registration follows successful account provisioning in the existing
Phone/SAR setup flow of SPEC Section 13.1. The account identifier, selected
SAR, payment, and static-data enrollment are established there. This extension
uses the same setup exchange, which must provide confidentiality and
server authentication bound to the selected `SarId` and setup account.

1. Phone derives the upload key and constructs its first
   `DynamicRescueUpload` using that key.
2. Through the protected setup exchange, Phone sends
   `canonical_encode(dynamic_update_auth_key, first_upload)`, with type
   `tuple<bytes32, DynamicRescueUpload>`.
3. SAR requires the upload identifier to match the provisioned account and the
   protocol version to match the setup exchange. If a key already exists, SAR
   requires a constant-time equality check with that key; a different key is
   rejected. Existing credentials and history are preserved.
4. SAR authenticates `first_upload` using the supplied key and applies the
   ordinary upload rules. On acceptance, SAR establishes the key if needed.
   Credential establishment and durable upload acceptance must both complete
   before SAR returns its signed receipt. A rejected first upload cannot
   establish or replace the credential.
5. Phone verifies that receipt. It confirms both upload registration and the
   first accepted upload, completing the dynamic-data step of SAR setup.

The first upload's signed receipt serves as the setup synchronization
acknowledgment. A lost reply is retried with the exact registration tuple.
If the first upload was accepted, SAR returns its original receipt. Knowledge
of the public identifier alone cannot authorize registration for an existing
account or replace its credential. The root `doxing_key_for_sar` is not sent
to SAR during registration.

The confidentiality and account-authentication guarantees of SAR setup are
prerequisites for this exchange. SPEC Section 13.1.1 requires a binding among
selected SarId, registration profile, invoice, and provisioned account; public
identifier knowledge or payment-metadata replay cannot authorize enrollment.
The deployment must document and test its transport and provisioning mechanism.
No separate Phone identity or second registration service is introduced.

### Later uploads and replacement Phones

After initial registration, Phone sends `DynamicRescueUpload` directly using
the established account key. A replacement Phone uses the same procedure with
its newly generated device ID. Payment and static-data enrollment are not
repeated for device replacement.

The account remains bound to its registration protocol version. Replacement
Phones and SAR use that profile for authentication, receipt verification, and
historical decoding. A software update must preserve access to accepted data;
a different profile cannot silently replace the credential or reinterpret
stored uploads.

### Upload outcomes

Upload identity is `(doxing_data_identifier, device_id, upload_id)`. SAR
validates encoding and authentication before comparing the canonical bytes of
the complete upload. Transport framing is excluded from the comparison.

| Upload | Result |
| --- | --- |
| New upload identity accepted by SAR | Append once and return a signed receipt |
| Accepted identity with identical canonical bytes | Return the original signed receipt without another append |
| Accepted identity with different canonical bytes | Reject the conflict and preserve the accepted upload and receipt |
| Same upload ID under another account or device ID | Treat as a separate upload under that account's authentication rules |

Phone retries the complete original upload after a missing reply. A missing
reply alone does not establish whether acceptance occurred. Re-encrypting the
same plaintext with a new IV creates different bytes and conflicts with an
accepted upload under the same identity. Concurrent delivery follows the same
rules; conflicting submissions under one identity cannot both be accepted.
Exact retry also provides receipt retrieval.

### Durability and activation

SAR accepts an upload durably before releasing its receipt. Retention applies
from acceptance, including when the reply is lost.

SAR crash recovery means restarting SAR or restoring its stored state after a
service failure. Within the deployment's supported failure conditions, it
preserves accepted uploads and their original receipts. Incomplete restoration
must be detected and cannot be presented as complete history. Phone replacement
and reconstruction of its account credential are separate operations described
above.

After valid duress activation, SAR uses the Boomlet-provided
`doxing_key_for_sar` and each stored device ID to derive the required data keys.
It makes every retained upload and receipt available to its rescue application.
Retrieval, decryption, interpretation, and SAR crash recovery preserve the fixed
acknowledgment and observability requirements of SPEC Sections 16.4–16.6.

## Security considerations

The protocol cannot establish whether payload data are true, fresh, ordered,
or useful. Interpretation belongs to the rescue application. Receipt signatures
attest acceptance of encrypted bytes. Device IDs identify histories; they do
not authenticate physical devices or restrict an account credential to one
history.

Durability and detection of incomplete SAR crash recovery rely on SAR retaining
the necessary data and recovery state. Their mechanisms and operational failure
assumptions belong to SAR deployment documentation. The protocol cannot force
a malicious SAR to preserve or disclose its storage.

Rescue-data confidentiality retains the password assumptions of ADR 0005.
Disclosure of `doxing_key_for_sar` allows derivation of all device-data keys
under that root. Traffic timing and ciphertext sizes retain the metadata risks
already described in the main specification.

## Conformance requirements

| Property | Required result |
| --- | --- |
| First registration | Only the provisioned setup account can establish its upload key. The first signed upload receipt confirms registration and acceptance. |
| Registration retry | Lost replies and interrupted registration preserve established credentials and accepted history. A different proposed key is rejected. |
| Authentication | Wrong keys, changed authenticated fields, and context mismatches are rejected. |
| Exact retry | Repeated delivery returns the original signed receipt without another append, including after SAR crash recovery and under concurrent delivery. |
| Conflict | Different bytes under the same account, device, and upload ID cannot both be accepted. Include changed-IV cases. |
| Device separation | The same upload ID under different device IDs identifies separate entries. Replacement needs no new device enrollment. Account credentials remain valid across those IDs. |
| Non-erasure | Later uploads, replacement, and registration retries preserve accepted entries and receipts. |
| SAR crash recovery | Accepted history and original receipts survive SAR restart or state restoration within supported failure conditions; an incomplete result cannot be reported as complete. |
| Payload handling | The encrypted plaintext is canonical `bytes`; payload meaning does not affect protocol processing. All retained entries remain available to rescue. |
| Cryptographic encoding | Shared vectors agree on KDF inputs, envelope context, upload CMAC, envelope hash, and receipt signature. Wire-size boundaries follow SPEC Section 8.3. |
| Duress behavior | Registration and upload changes preserve SPEC Sections 16.4–16.6 and Boomlet's existing key-release behavior. |
| Compatibility | Where earlier ciphertext exists, its original profile and decoding rules remain identifiable and usable. |

## Integration checklist

### Completed design integration

- [x] Adopt history retention in the roadmap and record DG-11 and DG-40 for
  independent security review.
- [x] Add SAR credential, immutable registration profile, device histories,
  receipts, and recovery state to SPEC Section 7.5.
- [x] Reserve retired schema ID 11; allocate upload/receipt IDs 30/31, version 1,
  sequential field IDs; register plaintext `bytes`, registration tuple, and
  receipt domain; regenerate the wire catalog.
- [x] Add exact keys, context, CMAC, receipt rules, and dynamic-context numeric
  limits to SPEC Sections 8–10; publish focused shared vectors.
- [x] Integrate protected first registration, account binding, receipt checks,
  replacement, and retries in SPEC Section 13.1 and setup contracts, preserving
  static verification and Section 13.9 finalization.
- [x] Integrate retry, crash-recovery requirements, and complete-history rescue
  access with the existing placeholder and fixed acknowledgment contract.
- [x] Consolidate conformance requirements in SPEC Section 21; add focused
  vector and bounded acceptance-model checks.
- [x] Update crypto notation and affected setup, withdrawal, and duress source
  diagrams, including `C-SAR-STORE-SEAL` and `C-SAR-STORE-OPEN` with device keys.
- [x] Align DESIGN, GLOSSARY, and supporting documentation; record adoption and
  compatibility here. Prepare the security review handoff.
- [x] Map dynamic failures to SPEC Section 18.1 classes.

### Evidence still required

- [ ] Independently reassess the security model using the
  [review note](../security_models/security_model_update_note.md).
- [ ] Validate the protected transport and provisioned-account binding with a
  real implementation, including identifier-only and payment-replay attacks.
- [ ] Pin the production `PROTOCOL_VERSION` value and canonical type, then
  independently reproduce vectors with the implementation revision recorded.
  Focused vectors explicitly use the test profile `u16(1)`.
- [ ] Validate capacity, independent deletion authority after setup retirement,
  storage fault injection, recovery witnesses, and detection of incomplete
  restoration under documented deployment failure conditions.
- [ ] Run parallel service acceptance and real safe/duress timing and
  observability tests with large, unavailable, and partly undecryptable histories.
- [ ] Verify retained legacy profiles and decoding with actual historical data.

### Optional

- [ ] Define cross-version account migration if required, preserving original
  credentials and decoding rules for retained history.

### Reproduction

Run `python3 scripts/generate_wire_catalog.py --check` and
`python3 scripts/check_dynamic_rescue.py` from the repository root. The latter
requires Python's `cryptography` package and compares
[`dynamic_rescue_vectors.json`](../spec/dynamic_rescue_vectors.json) with
recomputed exact bytes. Its SQLite acceptance model checks interruption,
restart, conflict serializations, and an externally supplied restoration witness.
It does not establish deployment durability or duress timing.
