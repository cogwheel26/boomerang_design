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
| Reject rollback | Satisfied by transactional append and an independent high-water commitment |
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

| Area | Current version | Proposed version |
| --- | --- | --- |
| Payload | Protocol schema and source timestamp | Bounded bytes interpreted by SAR implementation |
| Storage | Unspecified update handling | Append every accepted encrypted payload |
| Identity | No upload or device ID | Random `upload_id` and random persistent `device_id` |
| Encryption key | `doxing_key_for_sar` | Device-separated key derived from `doxing_key_for_sar` |
| Authentication | Encrypted envelope | Envelope plus upload authenticator |
| Acknowledgment | Unspecified synchronization acknowledgment | Signed receipt for exact encrypted bytes |
| Deletion | Undefined | Phone has no erasure authority |
| Ordering and expiry | Undefined | Remain outside the protocol |

The existing identifier derivation, encryption profile, Boomlet-provided
`doxing_key_for_sar`, and fresh-IV rule stay unchanged. The envelope context
additionally binds `device_id` and `upload_id`.

An older upload cannot replace a newer one because uploads never replace each
other. SAR and its implementation order and assess retained data after
decryption.

## Requirements

### DRD-SR-01 Phone non-erasure

No Phone message, credential, secret, or recovery procedure can make SAR hide,
delete, truncate, reset, or forget an accepted payload.

No later upload can revoke, supersede, or reduce access to an accepted and
receipted payload. SAR provides the complete authenticated upload history to
its rescue implementation.

SAR retains every accepted encrypted payload while a related Boomerang setup
may remain active. Later deletion requires independent SAR authority. Phone
cannot request, approve, or accelerate it.

### DRD-SR-02 Payload agnosticism

The protocol treats the payload as bounded bytes. It defines no format, type,
timestamp, parser, ordering, freshness, or semantic validation rule.

Payload meaning cannot affect acceptance, retention, receipts, retries, or the
withdrawal protocol.

### DRD-SR-03 Durable append

Every authenticated upload with a new `upload_id` is appended atomically. Exact
retries are idempotent. No accepted upload replaces another.

### DRD-SR-04 Phone replacement

Each Phone generates a random persistent `device_id`. A replacement Phone uses
a new value; no additional authorization exchange is introduced.

```text
device_data_key = KDF(
  doxing_key_for_sar,
  "Boomerang/sar_dynamic_device_data_key",
  device_id
)
```

The public `device_id` is key-diversification input, not proof of device
identity. SAR derives every historical `device_data_key` from the
Boomlet-provided `doxing_key_for_sar` during duress. Phone replacement therefore
does not affect earlier uploads. This adds no device authorization or
revocation; an old Phone may still append data but cannot erase or supersede
accepted uploads.

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
  encrypted_payload_hash: bytes32,
  received_at: u64
}
```

The envelope context binds the identifier, device ID, and upload ID. SAR signs
the receipt. `received_at` is SAR metadata, not payload ordering or expiry.

## Processing

Phone and SAR establish a KDF-separated `dynamic_update_auth_key` during
registration. The upload authenticator is AES-CMAC over every preceding upload
field. The key authorizes upload and receipt retrieval only.

| Upload | Result |
| --- | --- |
| New upload ID | Store atomically and return a signed receipt |
| Known upload ID with identical bytes | Return the original receipt |
| Known upload ID with different bytes | Reject |

SAR enforces ciphertext size and account capacity before acceptance. Capacity
pressure can reject a new payload but cannot evict an accepted one.

The stored payloads, retry index, and receipts are transactional and backed up.
Recovery rejects a stored set below an independently retained high-water
commitment.

After valid duress activation, SAR uses the Boomlet-provided
`doxing_key_for_sar` and each stored `device_id` to derive the required keys. It
makes every retained payload and receipt available to its rescue
implementation. Decryption and interpretation occur after the fixed
placeholder acknowledgment and cannot affect its observable behavior.

## Application checklist

| Tracked files | Required change |
| --- | --- |
| `spec/SPEC.md` | Reserve retired schema ID 11; define the upload, receipt, device ID, device-data KDF label, envelope context, authentication, append-only storage, recovery, limits, failures, activation, and conformance rules. |
| `spec/wire_catalog.json`, `spec/wire_catalog.txt` | Replace `DynamicDoxingData` with bounded bytes, register the new objects, and regenerate the text catalog. |
| `no_prose_crypto_contracts.md` | Define the device-data KDF, upload authenticator, and device-and-upload-ID-bound stored-data context. |
| `adr/0005-user-chosen-doxing-password.md` | Record the derived upload-authentication key and the effect of password compromise. |
| `adr/README.md`, new `adr/0009-append-only-dynamic-rescue-data.md` | Record acceptance, rationale, compatibility impact, and residual risks. |
| `GLOSSARY.md` | Define dynamic upload, device ID, device-data key, upload ID, receipt, and append-only rescue history. |
| `DESIGN.md` | Replace current-data assumptions with complete-history retrieval and the malicious-Phone limitation. |
| `setup/README.md`, `setup/setup_development_contracts.md`, `setup/setup_no_prose_guards.md` | Specify device-ID generation, device-data key derivation, upload creation, authentication, receipt verification, retry, capacity, and non-erasure. |
| `setup/setup_protocol_development.puml`, `setup/setup_diagram_without_states.puml`, `setup/setup_diagram_without_states_without_prose_comments.puml` | Replace dynamic-record synchronization with upload and signed-receipt exchanges. |
| `duress_protection/README.md`, `duress_protection/duress_protection_withdrawal_diagram.puml` | Make the payload protocol-agnostic and retrieve the complete collection on activation. |
| `withdrawal/README.md`, `withdrawal/initiator_withdrawal_diagram_without_states.puml`, `withdrawal/non_initiator_withdrawal_diagram_without_states.puml`, `withdrawal/withdrawal_no_prose_fragments.puml` | Derive each device-data key from the Boomlet-provided key and replace singular dynamic-data decryption with complete-history retrieval and handoff to SAR implementation. |
| `security_models/README.md`, `security_models/architecture.md` | Record append-only storage, Phone non-erasure, payload agnosticism, rollback evidence, and residual false-data risk. |
| `security_models/assumption_register.md`, `security_models/attack_trees.md`, `security_models/audit_mappings.md` | Replace current-record and expiry assumptions with full-history guarantees and remaining malicious-Phone threats. |
| Tracked working registers | Replace `DynamicDoxingData` limits with ciphertext, upload-rate, capacity, and retention bounds; replace Phone delete authority with append-only upload authority. |

PlantUML sources change as listed. SVG files are not regenerated.

## Limits

The protocol cannot determine whether payload data is true, fresh, ordered, or
useful. A `device_id` does not establish which physical Phone produced an
upload. The SAR implementation handles those questions using the decrypted
payloads and receipt times.

The rules cannot stop a malicious SAR from destroying its own storage. Traffic
timing and ciphertext size can also leak information. Padded size classes can
reduce size leakage.

## Acceptance

Tests must cover upload, exact retry, upload ID collision, later-upload
non-supersession, complete-history delivery, Phone non-erasure, crash recovery,
capacity without eviction, payload agnosticism, Phone replacement, derivation
of every historical device key from the Boomlet-provided key, and unchanged
placeholder acknowledgment behavior.
