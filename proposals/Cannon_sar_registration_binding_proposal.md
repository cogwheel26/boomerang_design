# SAR registration binding proposal

Status: Proposed, not adopted.

## Problem

The first `DynamicRescueUpload` is authenticated with the key supplied in the
same request. SAR currently checks that its identifier matches a pending
account, but cannot check that the supplied key belongs to that identifier.
Payment and knowledge of an identifier cannot establish upload authority.
The specified confidential exchange also lacks a concrete binding to the
selected `SarId`.

## Proposed registration

Make the identifier a hash of the account upload key. Derive the key
without the current circular identifier input:

```text
dynamic_update_auth_key = kdf_counter_cmac_aes256(
  doxing_key_for_sar,
  "Boomerang/sar_dynamic_update_auth_key/v1",
  canonical_encode(PROTOCOL_VERSION),
  32
)
doxing_data_identifier = tagged_sha256(
  "Boomerang/doxing_data_identifier",
  dynamic_update_auth_key
)
```

The SAR-scoped root still determines the identifier, static-data encryption
key, and dynamic-data keys. Phone, Boomlet, and Iso use the same derivation.
SAR checks the identifier against the supplied upload key before creating a
pending registration or accepting static data. An existing account accepts
only its stored key. SAR never needs the root during registration.

The Phone–SAR path prioritizes availability. It uses TLS 1.3 over a clearnet
endpoint by default and may offer several endpoints for retries. Endpoint
addresses are routing hints; the selected `SarId` key is the authority. The
`SarId` Tor address remains available for the other setup and withdrawal
exchanges.

Use the authenticated channel for invoice issuance and submission:

1. Phone connects to an endpoint and sends a fresh 32-byte challenge.
   SAR signs `canonical_encode(PROTOCOL_VERSION, selected_sar_id,
   phone_challenge, tls_exporter)` under domain
   `Boomerang/setup/sar_registration_channel` with its `SarId` key.
   `tls_exporter` is the current connection's 32-byte
   [TLS exporter](https://www.rfc-editor.org/rfc/rfc9266.html) value. Phone
   verifies the signature before sending the upload key or rescue data. TLS
   early data is disabled.
2. Phone sends the identifier and upload key inside that channel. SAR checks
   their relationship and creates a pending registration with a unique invoice
   bound to the identifier, selected SAR, and registration profile. A pending
   invoice does not reserve the account.
3. After payment, Phone sends the invoice proof, static-data envelope, and
   first upload through an authenticated registration channel. SAR checks the
   same key and identifier, verifies payment for that pending invoice and SAR,
   and validates the first upload. It commits invoice use, static envelope,
   profile, key, first upload, and original signed upload receipt atomically.
4. An exact retry returns the original receipt. A conflicting registration
   cannot replace the static envelope, key, or upload history. Phone verifies
   the receipt before reporting registration complete.

Reconnection repeats channel authentication. The paid invoice identifies the
pending attempt; neither the invoice nor its payment proof is upload authority
without the matching key. Later uploads, exact retries, and replacement Phones
use the same clearnet channel profile and may switch endpoints. They use the
existing upload key and signed receipts; the key is not sent again. All
endpoints for one `SarId` must use consistent account history and original
receipts. Clearnet routing exposes connection metadata, while TLS protects
registration values and upload metadata in transit.

## Specification and implementation boundary

SPEC should define the key and identifier derivations, the check before
account creation, the invoice binding, atomic registration, and the channel's
required authentication, confidentiality, integrity, and replay properties.
The mandatory Phone–SAR transport profile should pin endpoint discovery and
failover, TLS configuration, certificate handling, exporter use, and framing.
Registration is incomplete until that profile and its conformance tests exist;
a generic "confidential exchange" is insufficient. Tor must not be required
for Phone registration or later uploads.

Update the setup flow, development guards, diagrams, wire vectors, and
identifier derivations in `SPEC.md` together. The existing upload and receipt
schemas need no new fields. Record the changed registration threat boundary in
`security_models/security_model_update_note.md` for independent security-model
review; do not edit the security models as part of the integration.

Conformance checks should cover wrong SAR or profile, a substituted channel,
identifier and key mismatch, replayed or reassigned payment proof, conflicting
first registration, lost receipt, restart during commit, and exact retry through
another endpoint. A guessed password can still yield the account key; the
proposal does not strengthen the password itself.
