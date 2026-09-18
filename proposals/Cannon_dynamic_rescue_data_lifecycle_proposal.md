# Dynamic rescue-data lifecycle proposal

| Item | Value |
| --- | --- |
| Status | Draft, not adopted |
| Phase 1 priority | 1 |
| Normative baseline | [`SPEC.md`](../spec/SPEC.md) at `8ad77efabe03385d60733827fe55b3f988519c65` |
| Related gaps | DG-11, DG-40 |

## Current status

`SPEC.md` currently defines `DynamicDoxingData` with `schema_id`, `captured_at`,
and `payload`. Phone encrypts it with a fresh IV under the
`"sar_dynamic_data"` context. SAR stores it under `doxing_data_identifier` and
acknowledges synchronization.

The specification does not define upload identity, durable append, retry,
deletion, rollback, or conflict rules. It also does not define expiry or how an
update becomes current. DG-40 remains open.

## Roadmap goal

> Define version ordering, expiry, clock-skew handling, rollback rejection, and
> conflict handling such that SAR can identify the current rescue-data update
> and accept a correction without allowing an older valid update to replace it.

## Reason for divergence

The roadmap assumes one current record. Dynamic payloads may instead be a
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

Acceptance requires updating the roadmap from current-record selection to
authenticated append, complete-history retention, and rollback detection.

## Proposed changes

| Area | Proposed behavior |
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
canonical encoding, fixed-width types, and encoded-size limits.

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
It authorizes upload and receipt retrieval only.

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
prerequisites for this exchange. Its integration must retain those guarantees
without introducing a separate Phone identity or a second registration service.

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

## Integration todo list

### Required

- [ ] Adopt the history-retention objective in the roadmap and align DG-11,
  DG-40, and their assumptions with the proposal's guarantees.
- [ ] Update SPEC Section 7.5 with the account upload credential, registration
  profile version, device-indexed uploads, and signed receipts as logical state.
- [ ] Assign unused schema IDs to the upload and receipt, schema version 1,
  and field IDs starting at 1 in declared order. Reserve retired schema ID 11.
  Map `sar_dynamic_data` to plaintext type `bytes`; register the registration
  tuple and `Boomerang/setup/sar_dynamic_receipt` content type in
  `spec/wire_catalog.json`, then regenerate `spec/wire_catalog.txt`.
- [ ] Add the exact key derivations, stored-data context, upload CMAC, and
  receipt rules to SPEC Sections 8–10. Set their encoded-size limits under
  Section 8.3 and publish shared vectors.
- [ ] Extend SPEC Section 13.1 and the setup contracts with first-device
  registration after account provisioning. Specify the protected setup
  transport's binding to `SarId` and the provisioned account. Replace the
  dynamic synchronization acknowledgment with the first signed upload receipt.
  Preserve static-data verification and Section 13.9 SAR finalization.
- [ ] Integrate retry and SAR crash recovery guarantees into the existing failure
  and recovery requirements, and complete-history access into Section 16. Keep
  the placeholder format, timing, and Boomlet key release unchanged.
- [ ] Consolidate the conformance requirements in SPEC Section 21 and extend
  the wire vectors and protocol scenarios for registration, retries, conflicts,
  device separation, SAR crash recovery, and duress observability.
- [ ] Update `no_prose_crypto_contracts.md` and the affected setup, withdrawal,
  and duress PlantUML sources. Reuse `C-SAR-STORE-SEAL` and `C-SAR-STORE-OPEN`
  with `device_data_key`. Do not render diagrams or regenerate SVG files.
- [ ] Align `DESIGN.md`, `GLOSSARY.md`, setup and withdrawal documentation,
  the security model, and ADR 0005. Record the decision and compatibility
  impact in a new ADR.

### Optional

- [ ] Map upload conflicts and registration failures to the existing SPEC
  Section 18.1 failure classes, using the existing error mechanism.
- [ ] Define cross-version account migration if that capability is required,
  preserving original credentials and decoding rules for retained history.
