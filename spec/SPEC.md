# Boomerang Protocol Specification

Intended status: Informational
Status: Research draft, not production ready.

## Abstract

Boomerang is a Bitcoin cold-storage protocol intended for threat models that include physical coercion. It combines:

- a Taproot spending policy with an early 5-of-5 Boomerang branch and later normal-key fallback branches;
- a secure-element key share that is unavailable to hosts and exportable only
  through the authenticated Boomlet-to-Boomletwo backup flow;
- a bounded but unpredictable withdrawal delay enforced by secret per-device thresholds;
- repeated, plausibly deniable duress checks;
- Search and Rescue notification embedded in ordinary withdrawal traffic;

This document defines the Boomerang protocol profile: actors, data model, cryptographic profile, setup and withdrawal state machines, message semantics, replay protections, failure behavior, and known open issues.

## Table of contents

- [1. Status and requirements language](#1-status-and-requirements-language)
- [2. Protocol profile](#2-protocol-profile)
- [3. Goals and non-goals](#3-goals-and-non-goals)
- [4. Terminology and actors](#4-terminology-and-actors)
- [5. Architecture and trust boundaries](#5-architecture-and-trust-boundaries)
- [6. Protocol parameters](#6-protocol-parameters)
- [7. State](#7-state)
- [8. Canonical data model](#8-canonical-data-model)
- [9. Cryptographic profile](#9-cryptographic-profile)
- [10. Protocol objects](#10-protocol-objects)
- [11. Descriptor](#11-descriptor)
- [12. Setup state machine](#12-setup-state-machine)
- [13. Setup protocol](#13-setup-protocol)
- [14. Withdrawal state machine](#14-withdrawal-state-machine)
- [15. Withdrawal protocol](#15-withdrawal-protocol)
- [16. Duress protocol](#16-duress-protocol)
- [17. Replay resistance and binding](#17-replay-resistance-and-binding)
- [18. Failure and recovery behavior](#18-failure-and-recovery-behavior)
- [19. Security considerations](#19-security-considerations)
- [20. Privacy considerations](#20-privacy-considerations)
- [21. Conformance requirements](#21-conformance-requirements)
- [22. Open issues](#22-open-issues)
- [23. Normative references](#23-normative-references)
- [Appendix A: Duress display vocabulary](#appendix-a-duress-display-vocabulary)

## 1. Status and requirements language

Boomerang is research-stage. This specification describes the intended protocol
and its current security boundaries; it does not assert production readiness,
hardware certification, or complete operational procedures. This document is
not an Internet Standards Track specification.

The key words `MUST`, `MUST NOT`, `REQUIRED`, `SHOULD`, `SHOULD NOT`, and
`MAY` in this document are to be interpreted as described in BCP 14
[RFC2119] [RFC8174] when, and only when, they appear in all capitals, as shown
here.

An `OPEN ISSUE` identifies a design choice that is not yet fixed. An implementation that chooses a value for an open issue MUST identify that choice as an implementation profile and MUST NOT claim interoperability with a different profile without conformance testing.

## 2. Protocol profile

The profile specified here has:

- exactly 5 peers;
- a 5-of-5 Boomerang spending branch;
- one active Watchtower (`WT`) for a ceremony;
- one selected SAR identity per peer;
- one active Boomlet and at most one inactive Boomletwo backup per peer;
- one Secure Terminal (`ST`) per peer;
- Bitcoin Taproot, Schnorr signatures, MuSig2, absolute block-height timelocks, and PSBT;
- AES-256-CBC with PKCS#7 padding and AES-CMAC encrypt-then-MAC for confidentiality and integrity.

Changing the peer count, primary threshold, fallback tree, cryptographic profile, or setup checkpoint sequence creates a different protocol profile.

This document is an applicability statement for the profile above. At the moment, it is not a
generic framework for arbitrary peer counts, threshold policies, rescue-service
topologies, or cryptographic suites.

## 3. Goals and non-goals

### 3.1 Goals

Boomerang is designed to:

- make the primary withdrawal completion time bounded but not known in advance;
- provide recurring opportunities to signal coercion without visibly changing protocol flow;
- preserve eventual recoverability through later deterministic fallback branches;
- require no Bitcoin consensus changes;
- use symmetric primitives available on a broad range of Java Card devices.

### 3.2 Non-goals

Boomerang does not:

- eliminate coercion or guarantee rescue;
- hide all metadata from WT, SAR, Tor observers, or compromised endpoints;
- make an untrusted ST or compromised Boomlet safe;
- define SAR legal authority or physical-response procedures;

## 4. Terminology and actors

- `Peer`: one joint custodian. Peers are indexed `0..4`.
- `User`: the human operator for one peer.
- `Iso`: the peer's isolated offline environment.
- `Niso`: the peer's online coordination environment.
- `Boomlet`: the active secure element.
- `Boomletwo`: the inactive backup secure element.
- `ST`: the air-gapped Secure Terminal used for trusted display and user input.
- `WT`: the active Watchtower coordinating setup and withdrawal.
- `SAR`: the Search and Rescue service selected by a peer.
- `Phone`: the device registering and updating encrypted rescue data with SAR.
- `normal key`: mnemonic-backed recoverable key held by Iso.
- `boom key share`: MuSig2 key share held by Boomlet, unavailable to hosts and
  exportable only inside the authorized Boomletwo backup envelope.
- `boom_pubkey`: the aggregate of the peer's normal public key and Boomlet public share.

## 5. Architecture and trust boundaries

### 5.1 Per-peer components

Each peer controls:

- Iso, deriving the normal private key;
- Niso, with Bitcoin RPC and Tor connectivity;
- Boomlet, storing host-inaccessible keys and protocol state;
- ST, displaying transaction identifiers and collecting duress answers;
- Phone, sending encrypted rescue data;
- optionally, a Boomletwo.

### 5.2 External components

The protocol uses:

- the Bitcoin network;
- at least one Bitcoin RPC endpoint per Niso;
- Tor for peer and WT communication;
- one active WT;
- one SAR per peer.

### 5.3 Trust assumptions

The current security argument assumes:

- at least one peer remains honest and follows the Boomerang path in setup;
- Boomlet prevents extraction or unauthorized use of its private material;
- ST preserves display and input integrity;
- Iso is isolated during key derivation and final signing;
- cryptographic primitives are correctly implemented;
- WT and SAR remain available during ceremonies;
- users start rollover or recovery before fallback timelocks make coercion predictably useful.

WT and SAR are not custody signers, but they are security-critical. WT can delay or censor progress. SAR can stop the ceremony by failing to respond, mishandle rescue data, or reveal metadata.

## 6. Protocol parameters

The following symbolic parameters are part of the implementation profile:

| Parameter | Meaning | Required constraint |
| --- | --- | --- |
| `PROTOCOL_VERSION` | Wire and semantic profile version | Identical for all participants |
| `MIN_TRIES_FOR_DIGGING_GAME_IN_BLOCKS` | Minimum mystery value | Positive integer |
| `MAX_TRIES_FOR_DIGGING_GAME_IN_BLOCKS` | Maximum mystery value | At least the minimum |
| `DURESS_CHECK_INTERVAL_IN_BLOCKS` | Mean duress-check interval parameter | Positive integer |
| `REQUIRED_MINIMUM_DISTANCE_IN_BLOCKS_BETWEEN_PING_AND_PONG` | Minimum effective progress spacing | At least 1 |
| `FRESHNESS_TOLERANCES` | Complete mapping of per-message block-height tolerances | Every value is non-negative and fixed by the implementation profile |
| `TOLERANCE_IN_BLOCKS_FROM_CREATING_PING_BY_OTHER_PEERS_TO_REVIEWING_THE_PING_IN_PEER_BOOMLET` | Maximum age of a peer ping used by Boomlet for local counter advancement | Non-negative integer |
| `JUMP_IN_BLOCKS_IF_LAST_SEEN_BLOCK_LAGS_BEHIND_NISO_EVENT_BLOCK_HEIGHT_IN_BOOMLET` | Maximum local `last_seen_block` advance per successful round | Positive integer |

Each participant MUST run a binary or implementation profile whose behavior is
identified by `PROTOCOL_VERSION`. Every signature digest, envelope context,
setup identifier hash, and checkpoint hash MUST include `protocol_version` as
authenticated context. Timing and digging-game constants are
implementation-profile constants, not setup inputs or setup-agreement fields.

`OPEN ISSUE`: safe production values for mystery bounds, freshness tolerances,
duress cadence, and block-height jump limits are not yet selected.


## 7. State

### 7.1 Boomlet long-lived state

Boomlet stores:

- identity private key and public key;
- MuSig2 private share and public share;
- normal public key;
- ST identity public key;
- Tor secret key;
- selected SAR identity and `doxing_key`;
- `duress_consent_set`;
- signed local `PeerSetupRecord`;
- active `setup_instance_id`;
- `boomerang_params`;
- `setup_checkpoint`;
- backup-complete flag;
- replay memory needed to reject completed setup instances and active withdrawal replays.

During an active setup or withdrawal, Boomlet also holds volatile ceremony state
shown in the diagrams, including outstanding ST challenge nonces, candidate
`duress_check_space`, transaction review state, `withdrawal_id`,
`approved_withdrawal_id`, verified approval and commit collections, current
placeholder plaintext, the active withdrawal `mystery`, ping counters,
reached-peer state, and signing-session state.
Identity and MuSig2 private material MUST NOT be exported in plaintext or made
available to Iso, Niso, or the host. The only permitted export is the
authenticated, target-bound Boomlet-to-Boomletwo backup envelope during setup,
defined in Section 13.10.

### 7.2 Iso state

Iso takes and reconstructs:

- mnemonic, passphrase, and normal private key;
- network and descriptor-verification inputs;
- temporary setup-relay, backup-verification, and signing state.

Iso is not assumed to retain durable setup or withdrawal state when it is not
actively in use. It MAY lose state between ceremonies and during any interval of
a ceremony in which it is disconnected or idle. State needed for an active
backup-verification or signing exchange is volatile; if that state is lost, the
exchange MUST NOT silently continue and instead returns the relevant Section 18
failure class, stalls, retries from a fresh session, or requires explicit
abandonment when session-secret safety demands it.

### 7.3 Niso state

Niso stores:

- Bitcoin RPC configuration;
- Tor identity material provided by Boomlet;
- peer reachability records;
- active setup relay state, including signed peer records, WT identifiers,
  milestones, setup IDs, fingerprints, checkpoints, and payment messages until
  they are relayed or no longer needed;
- active withdrawal relay state, including PSBTs, transaction IDs, approval and
  commit collections, pings, pongs, reached-ping collections, and locally
  observed block heights;
- the latest locally observed block height.

Niso is not trusted to authorize spending. Boomlet and ST independently verify
critical data.

### 7.4 WT state

WT stores:

- registered setup agreements and peer identity keys;
- selected per-peer SAR routing information received during setup finalization;
- active ceremony `setup_instance_id`, `withdrawal_id`, and post-approval
  `approved_withdrawal_id`;
- approvals, approval-set attestations, commitments, latest pings, pongs, and
  reached pings;
- payment and service receipts;
- replay and deduplication state.

### 7.5 SAR state

SAR stores:

- `doxing_data_identifier`;
- AES-CBC/CMAC envelopes containing static and dynamic rescue data;
- payment or registration status;
- replay tuples for duress placeholders:
  `{approved_withdrawal_id, boomlet_identity_pubkey, duress_placeholder.iv}`;
- its identity keypair.

## 8. Canonical data model

### 8.1 Primitive types

The protocol data model uses:

- `bool`;
- `u8`, `u16`, `u32`, and `u64`, encoded unsigned and big-endian;
- fixed byte strings such as `bytes16`, `bytes32`, and `bytes33`;
- variable `bytes`;
- UTF-8 `text`;
- ordered `list<T>`;
- ordered heterogeneous `tuple<T...>`;
- versioned `struct` objects.

Text MUST be valid UTF-8 and normalized to Unicode NFC. Protocol labels are ASCII. Maps and floating-point numbers are forbidden.

`uint16_be(value)` and `uint32_be(value)` are fixed-width unsigned big-endian
encodings. `utf8(text)` returns the NFC-normalized UTF-8 bytes of `text`.
`zero_bytes_32` is exactly 32 zero bytes.

### 8.2 Canonical encoding

`canonical_encode(value)` is recursive and deterministic:

```text
null:    0x00
false:   0x01
true:    0x02
u8:      0x10 || value[1]
u16:     0x11 || value[2]
u32:     0x12 || value[4]
u64:     0x13 || value[8]
bytes:   0x20 || uint32_be(length) || value
text:    0x21 || uint32_be(utf8_length) || utf8_nfc_bytes
list:    0x30 || uint32_be(count) || canonical_encode(item_0) || ...
tuple:   0x31 || uint16_be(count) || canonical_encode(item_0) || ...
struct:  0x40 || uint16_be(schema_id) || uint16_be(schema_version)
              || uint16_be(field_count)
              || uint16_be(field_id_0) || canonical_encode(value_0)
              || ...
```

Struct fields MUST appear in ascending field-ID order. Unknown fields MUST be
rejected unless the schema version explicitly permits extensions. Duplicate
fields, non-minimal integers, invalid UTF-8, and trailing bytes MUST be
rejected. Each schema or message type supported by a `PROTOCOL_VERSION` has a
fixed positive maximum canonical encoded size. Implementations MUST reject
objects exceeding that schema or message type's limit before allocation or
decoding.

`canonical_encode(value_0, ..., value_n)` is shorthand for canonical encoding of
the ordered tuple containing exactly those values. It is not raw
concatenation.

Transport framing MAY add a length prefix or QR encoding, but signatures, hashes, CMACs, and identifiers operate on the canonical object bytes defined here.

### 8.3 Key encoding

- secp256k1 ECDH public keys are 33-byte compressed SEC1 encodings;
- BIP340 signing public keys are the corresponding 32-byte x-only encodings;
- private scalars are 32-byte big-endian values in the valid secp256k1 range;
- SHA-256 values and identifiers are 32 bytes;
- AES-CBC IVs and AES-CMAC tags are 16 bytes.

Invalid points, infinity, non-curve points, invalid scalars, and non-canonical encodings MUST be rejected.

### 8.4 Ordering

Peer setup records and identity public keys are ordered lexicographically by encoded 33-byte Boomlet identity public-key bytes. Duplicate identity keys or duplicate ordering keys MUST be rejected.

## 9. Cryptographic profile

### 9.1 Hashes

`sha256(bytes)` is SHA-256.

`tagged_sha256(tag, bytes)` is:

```text
tag_hash = sha256(utf8(tag))
sha256(tag_hash || tag_hash || bytes)
```

### 9.2 Random generation

- `random_bytes(n)` returns `n` bytes from an approved DRBG seeded with device entropy.
- `random_integer(min, max)` uses rejection sampling and is uniform over the inclusive range.
- `random_permutation(values)` is a uniform Fisher-Yates permutation using unbiased draws.
- Setup challenge nonces are 32 bytes.
- AES-CBC IVs are independently random 16-byte values.

Random values MUST NOT be reused where this specification requires freshness.

### 9.3 Identity signatures

Identity signatures use BIP340 Schnorr over secp256k1.

```text
signature_digest =
  tagged_sha256(
    "Boomerang/signature/v1",
    canonical_encode(PROTOCOL_VERSION, domain, content)
  )
```

`sign_message(private_key, domain, content)` signs with the active
implementation profile in the signature context and returns:

```text
SignedMessage {
  signer_identity_pubkey,
  domain,
  content,
  signature
}
```

`verify_signature(expected_pubkey, expected_domain, message_signed_by_signer)` verifies
the signer, domain, protocol-version signature context, canonical digest, and
BIP340 signature. A signature valid under another domain or `PROTOCOL_VERSION`
MUST NOT be accepted.

### 9.4 ECDH and key derivation

`entity_name` arguments to `channel_keys` are hardcoded protocol enum values,
not untrusted host-provided strings. The valid setup-channel values are
`"boomlet"`, `"st"`, `"wt"`, `"sar"`, and `"boomletwo"` unless a later profile
adds more entities.
Distinct names are compared by bytewise ASCII order of the fixed lowercase enum
labels, not locale collation or host-supplied strings.

`channel_keys(local_private_key, local_entity_name, peer_public_key, peer_entity_name, sender_public_key, receiver_public_key)`:

1. validates the peer compressed secp256k1 point;
2. derives the local public key from `local_private_key`;
3. verifies that `sender_public_key` and `receiver_public_key` are exactly the
   two public keys `local_public_key` and `peer_public_key`;
4. orders the two endpoint pairs by hardcoded entity name; when both endpoints
   have the same entity name, orders them by canonical public-key bytes;
5. performs scalar multiplication;
6. takes the 32-byte big-endian x-coordinate as `shared_secret`;
7. derives the channel key schedule:

```text
key_bytes =
  kdf_counter_cmac_aes256(
    shared_secret,
    "Boomerang/channel_keys/v1",
    canonical_encode(PROTOCOL_VERSION, endpoint_0_entity_name, endpoint_0_identity_pubkey, endpoint_1_entity_name, endpoint_1_identity_pubkey),
    128
  )

endpoint_0_to_1_keys = CbcCmacKeys {
  encryption_key = key_bytes[0..31],
  mac_key = key_bytes[32..63]
}

endpoint_1_to_0_keys = CbcCmacKeys {
  encryption_key = key_bytes[64..95],
  mac_key = key_bytes[96..127]
}
```

8. returns the `CbcCmacKeys` matching `sender_public_key -> receiver_public_key`;
9. erases the raw shared secret and any unused derived key material after
   derivation unless the full channel schedule is cached for the active channel.

Raw ECDH output MUST NOT be used as a traffic-encryption key or envelope-CMAC
key. It is used only as the SP 800-108 CMAC KDF input key. Channel KDF context
binds the protocol version, endpoint entity names, endpoint identity public
keys, and traffic direction. Envelope contexts therefore carry only the message
type plus the narrow replay scope needed for that message.

`aes256_cmac(key, bytes)` is NIST SP 800-38B AES-CMAC with a 256-bit AES key and the full 16-byte output. Java Card implementations may use `Signature.ALG_AES_CMAC_128`; `128` identifies the AES block and output length, while requiring a 256-bit key. Devices without a native CMAC API MAY implement SP 800-38B using their AES engine.

`kdf_counter_cmac_aes256(key, label, context, output_length)` is NIST SP 800-108 counter mode:

```text
block_i =
  aes256_cmac(
    key,
    uint32_be(i)
      || utf8(label)
      || 0x00
      || context
      || uint32_be(output_length * 8)
  )
```

Blocks start at `i = 1`, are concatenated, and are truncated to `output_length`.

`derive_cbc_cmac_keys(key_material, context)` is used for non-channel key
material, such as stored SAR data. It computes and returns the transient
internal record:

```text
key_bytes =
  kdf_counter_cmac_aes256(
    key_material,
    "Boomerang/cbc_cmac/key_schedule/v1",
    canonical_encode(context),
    64
  )

CbcCmacKeys {
  encryption_key = key_bytes[0..31],
  mac_key = key_bytes[32..63]
}
```

`CbcCmacKeys` is not canonically encoded or transmitted and therefore has no
wire schema ID. The two keys MUST remain distinct. Boomlet MAY cache them only
in transient memory for the active exchange and SHOULD erase them when that
exchange completes, stalls, or is explicitly aborted.

### 9.5 AES-CBC/CMAC envelope

Encryption uses AES-256-CBC with PKCS#7 padding and encrypt-then-MAC:

```text
CbcCmacEnvelope {
  version = 1,
  iv,
  ciphertext,
  tag
}
```

`cbc_cmac_encrypt(keys, context, content)`:

1. sets `iv = random_bytes(16)`;
2. sets `plaintext = canonical_encode(content)`;
3. sets `ciphertext = AES-256-CBC-PKCS7(keys.encryption_key, iv, plaintext)`;
4. sets:

```text
tag =
  aes256_cmac(
    keys.mac_key,
    canonical_encode(
      "Boomerang/cbc_cmac/envelope/v1",
      context,
      iv,
      ciphertext
    )
  )
```

5. returns `CbcCmacEnvelope{1, iv, ciphertext, tag}`.

Decryption MUST:

1. validate envelope version and lengths;
2. recompute and constant-time compare the full tag;
3. reject on tag failure without attempting CBC decryption;
4. decrypt and validate PKCS#7 padding only after successful authentication;
5. decode exactly one canonical object with no trailing bytes.

MAC, padding, and decoding failures MUST have the same externally observable rejection class. An explicit-IV encryption operation is allowed only to reconstruct a previously received envelope for equality verification; an IV MUST NOT encrypt a different plaintext under the same key.

`cbc_cmac_decrypt(keys, context, envelope)` is the complete decryption procedure above.

### 9.6 Envelope context

Peer-to-peer CBC-CMAC context is:

```text
canonical_encode(message_type, optional_scope_id)
```

`optional_scope_id` is absent for nonce-bound local challenge/response flows.
Otherwise it is exactly one of `setup_instance_id`, `withdrawal_id`, or
`approved_withdrawal_id`, according to the message's replay scope.

Every envelope context MUST include `message_type`. This is the cross-message
replay separator inside one channel and scope.

Endpoint identity, entity role, traffic direction, and protocol version are not
repeated in envelope contexts. They are provided by `channel_keys(...)`: the KDF
binds `PROTOCOL_VERSION`, endpoint entity names, endpoint identity public keys,
and returns distinct directional encryption and MAC keys. Setup-scoped contexts
also bind version transitively through `setup_instance_id`, whose preimage
includes `PROTOCOL_VERSION`.

After setup agreement, non-nonce setup contexts bind `setup_instance_id`. During
withdrawal approval, contexts bind `withdrawal_id` once it exists; after
unanimous approval, contexts bind `approved_withdrawal_id`.
`approved_withdrawal_id` transitively binds `setup_instance_id` through
`withdrawal_id`, so post-approval contexts MUST NOT repeat `setup_instance_id`
unless a later profile changes the ID derivation. ST preview messages before
`withdrawal_id` exists rely on the message type, directional channel keys, and
the nonce-bound preview object. Boomlet-ST duress challenge and response
envelopes also omit withdrawal IDs: they rely on the message type, directional
channel keys, and Boomlet's exact outstanding `duress_check_nonce`.

The first backup-state import into an empty Boomletwo uses
`canonical_encode("backup_state")`. Boomletwo does not know the authoritative
setup ID until it decrypts the exported state. The authenticated plaintext MUST
contain the setup ID, and the channel keys still bind the active Boomlet
identity, target Boomletwo identity, endpoint roles, direction, and protocol
version. Boomletwo MUST accept this import only while empty and MUST include the
imported ID in signed `BackupDone`.

SAR stored-data context, which exists before setup agreement, is:

```text
{
  protocol = "Boomerang",
  protocol_version,
  message_type = "sar_static_data" or "sar_dynamic_data",
  doxing_data_identifier
}
```

### 9.7 Bitcoin keys and MuSig2

Normal and Boomlet signing keys use secp256k1. `derive_public_key` performs standard scalar-to-public-key derivation. `derive_musig2_public_key` and interactive signing follow BIP327. Implementations MUST bind the aggregate key, participant list, transaction sighash, public nonces, and session state exactly as required by BIP327 and MUST prevent nonce reuse.

#### 9.7.1 Normal-key derivation

The normal key uses BIP39 mnemonic encoding and seed derivation, then BIP32
private-key derivation on secp256k1. The path is:

```text
m / 52102' / coin_type' / account' / 0 / key_index
```

`52102` is `0xcb86`, the first two bytes of `sha256("boomerang")`
interpreted as a big-endian integer. This purpose value is
Boomerang-profile-specific and does not claim BIP registration.

`coin_type` is `0` for Bitcoin mainnet and `1` for testnet, signet, and
regtest unless a later profile assigns separate test-network coin types.
`account` is a user- or implementation-profile-selected account number and
defaults to `0`. `key_index` is the non-hardened Boomerang setup key index
under external chain `0` and defaults to `0`.

`normal_pubkey` is the 32-byte BIP340 x-only public key derived from the child
private scalar. A BIP86 Taproot output-key tweak MUST NOT be applied to
`normal_pubkey`.

### 9.8 Protocol operation names

The sequence notation uses these exact operation names:

- `utf8(text)` returns the NFC-normalized UTF-8 bytes defined in Section 8.1.
- `generate_private_key()` creates a valid private scalar or service key using the approved device RNG and the key type required by its assignment.
- `derive_public_key(private_key)` returns the canonical public-key encoding for that key type.
- `canonical_public_key_bytes(public_key)` validates the public key and returns its exact canonical encoded bytes.
- `mnemonic_from_entropy(entropy_bytes)` encodes the supplied entropy as a BIP39 mnemonic.
- `derive_master_xpriv(mnemonic, passphrase)` derives the BIP32 master private key from the BIP39 seed.
- `derive_child_xpriv(parent_xpriv, index, hardened)` derives the indicated BIP32 child private key.
- `derive_musig2_public_key(boomlet_share_pubkey, normal_pubkey)` returns the BIP327 aggregate key for the ordered two-key participant list.
- `derive_tor_address(tor_secret_key)` returns the Tor v3 onion-service address corresponding to the service identity key.
- `construct_boomerang_descriptor(peer_ids, milestone_blocks)` performs the deterministic construction in Section 11.
- `create_duress_display_columns(space)` maps challenge values through
  `DURESS_DISPLAY_VOCABULARY`, creates five independent shuffles, and returns
  both the display columns and their display-to-original-index maps.
- `select_one_from_each(columns)` captures exactly one user choice from each display column.
- `map_to_original_indices(selection, display_maps)` returns the five corresponding indices in the original challenge list in column order.
- `pay(payment_info)` represents external payment execution and returns a receipt.
- `verify_payment(payment_receipt)` performs the service's payment verification and returns a boolean.
- `min(values...)` returns the smallest integer argument.
- `sha256(bytes)`, `tagged_sha256(tag, bytes)`, `canonical_encode(fields)`, `random_bytes(length)`, `random_integer(min, max)`, `random_permutation(values)`, `channel_keys(...)`, `derive_cbc_cmac_keys(...)`, `cbc_cmac_encrypt(...)`, `cbc_cmac_decrypt(...)`, `sign_message(...)`, and `verify_signature(...)` have the definitions given above.

Payment execution is outside Boomlet and does not alter the cryptographic requirements for the surrounding protocol messages.

## 10. Protocol objects

The following schemas define semantic field order. Implementations MUST assign stable schema and field IDs consistent with this order.

Schema names use `UpperCamelCase`. Values and fields use `snake_case`. A
peer-indexed value uses `i` as the index placeholder, so `peer_i_id` denotes
the `PeerId` value for peer `i`, and `peer_0_id` is the concrete value for peer
0. The unindexed name `peer_id` denotes a local `PeerId` value or the
`PeerSetupRecord.peer_id` field. These names are instances of `PeerId`, not
additional schemas.

Type annotations use the primitive types from Section 8.1, schema names,
`list<T>`, and `value`. `value` denotes any canonical value permitted by
Section 8.

```text
CbcCmacEnvelope {
  version: u8,
  iv: bytes16,
  ciphertext: bytes,
  tag: bytes16
}

SignedMessage {
  signer_identity_pubkey: bytes33,
  domain: text,
  content: value,
  signature: bytes64
}

MessageWithNonce {
  content: value,
  nonce: bytes32
}

PaddedMessage {
  content: value,
  padding: value
}

SarServiceFeePaymentInfo {
  service_fee_invoice: text,
  payment_deadline: u64,
  sar_id: SarId
}

WtServiceFeePaymentInfo {
  setup_instance_id: bytes32,
  service_fee_invoice: text,
  payment_deadline: u64,
  wt_id: WtId
}

DuressCheckSpace {
  space: list<u16>
}

WtId {
  wt_tor_address: text,
  wt_pubkey: bytes33
}

SarId {
  sar_tor_address: text,
  sar_pubkey: bytes33
}

StaticDoxingData {
  name: text,
  national_id: text,
  address_home: text,
  address_work: text,
  phone_number_mobile: text,
  phone_number_home: text,
  phone_number_work: text,
  trusted_person_name: text,
  trusted_person_address: text,
  trusted_person_phone_number: text
}

DynamicDoxingData {
  schema_id: u32,
  captured_at: u64,
  payload: bytes
}

ServicePaymentReceipt {
  service_id: text,
  invoice_reference: text,
  payment_proof: bytes
}

PeerId {
  boom_pubkey: bytes32,
  normal_pubkey: bytes32,
  boomlet_identity_pubkey: bytes33
}

PeerSetupRecord {
  peer_id: PeerId,
  peer_setup_nonce: bytes32,
  tor_address: text
}

MilestoneBlocks {
  milestone_block_0: u32,
  milestone_block_1: u32,
  milestone_block_2: u32,
  milestone_block_3: u32,
  milestone_block_4: u32,
  milestone_block_5: u32
}

BoomerangParamsSeed {
  ordered_peer_setup_records: list<SignedMessage>,
  wt_ids: list<WtId>,
  milestone_blocks: MilestoneBlocks
}

BoomerangParams {
  setup_instance_id: bytes32,
  peer_ids: list<PeerId>,
  wt_ids: list<WtId>,
  milestone_blocks: MilestoneBlocks,
  boomerang_descriptor: text
}

WtSetupReceipt {
  setup_instance_id: bytes32,
  boomerang_params_fingerprint: bytes32
}

SarSetupResponse {
  setup_instance_id: bytes32,
  doxing_data_identifier: bytes32,
  fingerprint_of_static_doxing_data_encrypted_by_doxing_key_for_sar: bytes32,
  iv_of_static_doxing_data_encrypted_by_doxing_key_for_sar: bytes16
}

WtSarSetupResponse {
  setup_instance_id: bytes32,
  content: SignedMessage,
  wt_suffix: text
}

BoomletBackupRequest {
  backup_boomlet_pubkey: bytes33,
  backup_normal_pubkey: bytes32
}

BackupDone {
  setup_instance_id: bytes32,
  backup_boomlet_pubkey: bytes33,
  boomlet_pubkey: bytes33
}

BoomletBackupState {
  setup_instance_id: bytes32,
  boomlet_identity_private_key: bytes32,
  boomlet_identity_public_key: bytes33,
  boomlet_musig2_private_share: bytes32,
  boomlet_musig2_public_share: bytes32,
  normal_public_key: bytes32,
  st_identity_public_key: bytes33,
  tor_secret_key: bytes,
  selected_sar_id: SarId,
  doxing_key: bytes32,
  duress_consent_set: list<u16>,
  peer_setup_record_signed_by_boomlet: SignedMessage,
  boomerang_params: BoomerangParams,
  setup_checkpoint: bytes32,
  sar_setup_response_signed_by_sar: SignedMessage,
  replay_state: value,
  backup_complete: bool
}

TxApproval {
  withdrawal_id: bytes32,
  approval_nonce: bytes32,
  event_block_height: u32
}

WtTxApproval {
  withdrawal_id: bytes32,
  event_block_height: u32
}

TxCommit {
  approved_withdrawal_id: bytes32,
  event_block_height: u32
}

Ping {
  approved_withdrawal_id: bytes32,
  last_seen_block: u32,
  ping_seq_num: u64,
  reached_mystery_flag: bool
}

Pong {
  approved_withdrawal_id: bytes32,
  event_block_height: u32,
  prev_pings: list<SignedMessage>
}
```

Object type, schema ID, signature domain, and envelope context identify the
transition. Signed wrappers and encrypted envelopes are not duplicated inside
the object unless explicitly shown.

`PaddedMessage` is the canonical outer object used when a signed withdrawal
commit or ping is bound to a `duress_placeholder`. `padding` is opaque to the
object schema and is included byte-for-byte in the signed canonical encoding.

The SAR placeholder acknowledgment intentionally has no separate status-bearing
object. Its canonical form is the SAR signature over the exact
`duress_placeholder` envelope, encrypted by SAR for the target Boomlet as
defined in Section 16.4.

`BoomerangParamsSeed.ordered_peer_setup_records` contains signed
`PeerSetupRecord` values sorted by encoded Boomlet identity public-key bytes.
`BoomerangParams.peer_ids` is the corresponding ordered list of `PeerId`
values.
`milestone_blocks` is always a `MilestoneBlocks` struct. .

`DynamicDoxingData.schema_id` identifies the canonical payload schema and
`captured_at` records its source timestamp. A service payment proof is opaque
to the protocol, but the receiving service MUST verify that it pays the
expected invoice, amount, service identity, and deadline.

`BoomletBackupState` is never host-readable. Boomlet encrypts it directly for
the authorized Boomletwo identity.

## 11. Descriptor

### 11.1 Key construction

For peer `i`:

```text
boom_pubkey_i =
  derive_musig2_public_key(
    boomlet_musig2_pubkey_share_i,
    normal_pubkey_i
  )
```

### 11.2 Taproot policy

In the policy notation below:

- `pk(key)` requires a valid BIP342 signature for `key`;
- `thresh(k, expressions)` requires at least `k` listed expressions;
- `after(height)` requires the transaction `nLockTime` to satisfy the absolute
  block-height lock and all input sequences to permit lock-time enforcement;
- `and(left, right)` requires both expressions.

The Taproot internal key MUST be unspendable. The script tree contains:

```text
and(thresh(5, pk(boom_pubkey_0)..pk(boom_pubkey_4)),
    after(milestone_block_0))

and(thresh(5, pk(normal_pubkey_0)..pk(normal_pubkey_4)),
    after(milestone_block_1))

and(thresh(4, pk(normal_pubkey_0)..pk(normal_pubkey_4)),
    after(milestone_block_2))

and(thresh(3, pk(normal_pubkey_0)..pk(normal_pubkey_4)),
    after(milestone_block_3))

and(thresh(2, pk(normal_pubkey_0)..pk(normal_pubkey_4)),
    after(milestone_block_4))

and(thresh(1, pk(normal_pubkey_0)..pk(normal_pubkey_4)),
    after(milestone_block_5))
```

Milestones MUST be strictly increasing in `milestone_block_0` through
`milestone_block_5` order. The Boomerang branch MUST be the earliest spendable
branch. Fallback branches use only normal keys and monotonically reduce the
threshold.

`construct_boomerang_descriptor(peer_ids, milestone_blocks)` accepts the `MilestoneBlocks` struct, maps its six fields to the six branches above,
and deterministically constructs and checksum-encodes this descriptor. Peers
MUST compare the exact descriptor string and the underlying Taproot output key.
Iso and Niso use local `network` configuration when deriving, displaying,
checking block height, or relaying network-specific Bitcoin data.

## 12. Setup state machine

Boomlet setup states are:

```text
EMPTY
  -> INSTALLED
  -> ST_ENROLLED
  -> PARAMS_REVIEWED
  -> PARAMETERS_AGREED
  -> WT_READY
  -> SAR_READY
  -> BACKUP_READY
```

Any verification failure returns the relevant Section 18 failure class and stalls
the current setup attempt. Restart from installation requires explicitly
abandoning the stalled attempt and using a fresh `peer_setup_nonce`. A completed
`setup_instance_id` MUST remain in memory.

Transition prerequisites:

| Transition | Required local proof |
| --- | --- |
| `EMPTY -> INSTALLED` | Successful key generation and applet initialization |
| `INSTALLED -> ST_ENROLLED` | Two nonce-bound consent rounds resolve to the same set |
| `ST_ENROLLED -> PARAMS_REVIEWED` | ST signature over the exact nonce-bound `setup_instance_id` |
| `PARAMS_REVIEWED -> PARAMETERS_AGREED` | All peers sign identical `boomerang_params_fingerprint` |
| `PARAMETERS_AGREED -> WT_READY` | Valid local `WtSetupReceipt` |
| `WT_READY -> SAR_READY` | Valid local WT wrapper and SAR response |
| `SAR_READY -> BACKUP_READY` | Valid local `BackupDone` and equal peer `setup_checkpoint` signatures |

## 13. Setup protocol

### 13.1 SAR registration

1. User gives Phone `doxing_password`, one selected `SarId`, and static rescue data. Dynamic rescue data is Phone-held captured state.
2. For that `SarId`, Phone computes:

```text
doxing_password_bytes = utf8(doxing_password)

doxing_key =
  tagged_sha256(
    "Boomerang/doxing_key",
    doxing_password_bytes
  )

sar_pubkey = sar_id.sar_pubkey
sar_pubkey_bytes = canonical_public_key_bytes(sar_pubkey)

doxing_key_for_sar =
  tagged_sha256(
    "Boomerang/doxing_key_for_sar",
    doxing_key || sar_pubkey_bytes
  )

doxing_data_identifier =
  tagged_sha256(
    "Boomerang/doxing_data_identifier",
    doxing_key_for_sar
  )
```

3. Phone registers the identifier and receives payment information.
4. After payment, Phone derives stored-data keys with `derive_cbc_cmac_keys(doxing_key_for_sar, "Boomerang/sar_stored_data")`.
5. Phone sends the payment receipt, identifier, static-data envelope, and dynamic-data envelope. Dynamic updates use the Phone-held dynamic rescue data captured at send time.
6. SAR verifies payment, stores the envelopes under the identifier, and acknowledges synchronization.
7. Dynamic updates use fresh IVs and the `"sar_dynamic_data"` context.

The identifier is a lookup value, not a secret. Rescue data confidentiality depends on the entropy of `doxing_password`.

### 13.2 Boomlet installation

1. Iso derives the normal key from entropy, mnemonic, and passphrase.
2. Iso installs Boomlet and supplies:
   - `normal_pubkey`;
   - `doxing_key`;
   - selected SAR identity.
   Protocol version and implementation-profile constants are loaded locally by
   Iso and Boomlet.
3. Boomlet generates:
   - identity keypair;
   - MuSig2 private and public share;
   - `boom_pubkey`.
4. Boomlet returns only its identity public key at this stage.

For peer `i`, installation constructs:

```text
boomlet_i_identity_private_key = generate_private_key()
boomlet_i_identity_pubkey =
  derive_public_key(boomlet_i_identity_private_key)

boomlet_i_musig2_private_share = generate_private_key()
boomlet_i_musig2_public_share =
  derive_public_key(boomlet_i_musig2_private_share)

boom_pubkey_i =
  derive_musig2_public_key(
    boomlet_i_musig2_public_share,
    normal_pubkey_i
  )
```

Boomlet does not receive or persist `doxing_password`.

### 13.3 ST pairing and consent enrollment

1. Iso relays Boomlet and ST identity public keys.
2. Boomlet generates:

```text
duress_check_space =
  DuressCheckSpace {
    space = random_permutation([1..193])
  }

nonce = random_bytes(32)
```

3. Boomlet sends an encrypted `MessageWithNonce{duress_check_space, nonce}` to ST.
4. ST decrypts, maps each integer through `DURESS_DISPLAY_VOCABULARY`, copies the list into five independently shuffled columns, and stores each display-to-original-index map.
5. User selects one country per column.
6. ST converts each displayed choice to the corresponding index in Boomlet's original list and returns `MessageWithNonce{indices, nonce}`.
7. Boomlet verifies the exact outstanding nonce and phase, resolves the indices, and stores the resulting unordered five-element set.
8. A second round uses a new challenge and nonce. The resolved set MUST equal the first set.

### 13.4 Peer setup record

After moving Boomlet to Niso:

1. Boomlet generates a Tor secret key and fresh setup nonce, then constructs
   its peer identity:

```text
peer_i_tor_secret_key = generate_private_key()
peer_i_setup_nonce = random_bytes(32)

peer_i_id =
  PeerId {
    boom_pubkey = boom_pubkey_i,
    normal_pubkey = normal_pubkey_i,
    boomlet_identity_pubkey = boomlet_i_identity_pubkey
  }
```

2. Boomlet derives
   `peer_i_tor_address = derive_tor_address(peer_i_tor_secret_key)`.
3. Boomlet constructs and signs its `PeerSetupRecord`:

```text
peer_i_setup_record =
  PeerSetupRecord {
    peer_id = peer_i_id,
    peer_setup_nonce = peer_i_setup_nonce,
    tor_address = peer_i_tor_address
  }

peer_i_setup_record_signed_by_boomlet_i =
  sign_message(
    boomlet_i_identity_private_key,
    "Boomerang/setup/peer_setup_record",
    peer_i_setup_record
  )
```

4. Boomlet sends Niso:
   - `peer_i_setup_record_signed_by_boomlet_i`;
   - the Tor secret key needed to operate the local onion service.
5. Niso verifies the record, derives the Tor address, and requires equality with the signed address.
6. ST displays the signed record to User.
7. Users exchange signed records over a secure out-of-band channel.

`peer_id` and `peer_setup_nonce` MUST NOT be separately transmitted beside the signed record.

### 13.5 Setup instance

`setup_instance_id` is the deterministic identifier for the canonical setup
seed of one setup attempt.

User-to-Niso peer-record input MAY be unordered. Niso verifies the five signed
records, requires its own exact signed record to occur once, sorts the records
by encoded Boomlet identity public-key bytes into `ordered_peer_setup_records`,
and forwards that ordered collection to Boomlet.

Boomlet performs a single pass over `ordered_peer_setup_records`. During
that pass it MUST verify strictly increasing identity-key encodings, reject
duplicates, verify every `PeerSetupRecord` signature under
`"Boomerang/setup/peer_setup_record"` using the active profile signature
context, require its exact signed local record to occur once, extract ordered
peer IDs and Boomlet identity keys, and construct or incrementally hash the
canonical `BoomerangParamsSeed`. Boomlet MUST reject an unordered collection;
Niso is responsible for supplying canonical order.

```text
boomerang_params_seed =
  BoomerangParamsSeed {
    ordered_peer_setup_records,
    wt_ids,
    milestone_blocks
  }

setup_instance_id =
  tagged_sha256(
    "Boomerang/setup_instance_id",
    canonical_encode(PROTOCOL_VERSION, boomerang_params_seed)
  )
```

`wt_ids` is the user-approved WT preference order and MUST be preserved.
Different peer records, WT identities or order, milestones, protocol versions,
or setup nonces produce a different identifier.

### 13.6 User setup review

1. Boomlet constructs
   `BoomerangParamsSeed{ordered_peer_setup_records, wt_ids, milestone_blocks}`
   from the setup inputs accepted from Niso. `BoomerangParamsSeed` MUST NOT
   carry `setup_instance_id` or a nested setup parameter structure.
2. Boomlet computes `setup_instance_id` from the canonical seed. It wraps
   that setup ID in a fresh nonce and encrypts the nonce-bound value for ST.
3. Niso forwards ST the outer `setup_instance_id`, the encrypted commitment,
   `ordered_peer_setup_records`, `wt_ids`, and `milestone_blocks`. The ordered
   seed fields are display input for ST and are not authenticated by Niso.
4. ST decrypts the commitment using the Boomlet-to-ST directional keys and a
   context containing the outer `setup_instance_id`. It requires the decrypted
   nonce-bound setup ID to equal the authenticated outer value.
5. ST constructs `BoomerangParamsSeed` from the ordered seed fields supplied
   beside the encrypted commitment. ST MUST reject malformed encodings,
   duplicate or non-increasing Boomlet identity-key order, and non-canonical
   seed fields before display. Boomlet remains responsible for full peer-record
   signature verification before constructing the commitment.
6. ST computes `setup_instance_id` using `PROTOCOL_VERSION` in the hash
   context. It MUST require the recomputed value to equal the decrypted
   nonce-bound setup ID and the authenticated outer `setup_instance_id`.
7. ST displays the ordered peer setup records, WT order, milestone blocks, and
   protocol version represented by the matched ordered seed fields and hash
   context.
8. User approves only after exact comparison of ordered peer records, WT order,
   and milestones against the intended BoomerangParams review values.
9. ST signs the exact nonce-bound `setup_instance_id` and encrypts it
   back to Boomlet under a context that includes the same `setup_instance_id`.
10. Boomlet verifies the ST signature and exact equality with the outstanding
    nonce-bound setup ID.

### 13.7 Setup agreement

Boomlet constructs:

```text
peer_ids =
  [record.peer_id for record in ordered_peer_setup_records]

boomerang_descriptor =
  construct_boomerang_descriptor(
    peer_ids,
    milestone_blocks
  )

boomerang_params =
  BoomerangParams {
    setup_instance_id,
    peer_ids,
    wt_ids,
    milestone_blocks,
    boomerang_descriptor
  }

boomerang_params_fingerprint =
  tagged_sha256(
    "Boomerang/boomerang_params",
    canonical_encode(boomerang_params)
  )
```

Every Boomlet signs the identical fingerprint under
`"Boomerang/setup/agreement"`. Each Boomlet verifies all five signatures,
checks each signer against the ordered peer setup records, and requires exact
content equality.

Any `PROTOCOL_VERSION` signature/hash context mismatch or fingerprint-content
mismatch returns `PARAMETER_MISMATCH` and stalls the setup attempt.


The first checkpoint is:

```text
setup_checkpoint =
  tagged_sha256(
    "Boomerang/setup_phase_checkpoint",
    canonical_encode(
      setup_instance_id,
      "parameters_agreed",
      zero_bytes_32
    )
  )
```

The signed `boomerang_params_fingerprint` authenticates this transition; a
separate signature over `setup_checkpoint` is unnecessary.

Each later setup checkpoint update uses the current `setup_checkpoint` value as
the predecessor input.

### 13.8 WT registration

1. Niso sends WT `setup_instance_id`, each signed `PeerSetupRecord`, and signed
   `boomerang_params_fingerprint`.
2. WT verifies signer identity, record/fingerprint correspondence, and equality
   of every signed fingerprint.
3. WT sends per-peer payment information bound to `setup_instance_id`.
4. After payment verification, WT signs
   `WtSetupReceipt{setup_instance_id, boomerang_params_fingerprint}`.
5. Boomlet verifies its local receipt.
6. Boomlet computes and signs:

```text
setup_checkpoint =
  tagged_sha256(
    "Boomerang/setup_phase_checkpoint",
    canonical_encode(
      setup_instance_id,
      "wt_ready",
      setup_checkpoint
    )
  )
```

7. Every peer verifies that all signed `setup_checkpoint` values are identical.

The local WT receipt is not hashed into `setup_checkpoint`.

### 13.9 SAR finalization

1. Boomlet derives `doxing_key_for_sar` and `doxing_data_identifier`.
2. Boomlet encrypts `{setup_instance_id, doxing_data_identifier}` for SAR.
3. Boomlet signs `{setup_instance_id, sar_id}` and encrypts it for WT.
4. WT verifies the signed setup-bound SAR identity and forwards the SAR envelope to that exact SAR with Boomlet identity and setup ID. WT MUST NOT substitute, select among, or fail over to another SAR identity inside the setup.
5. SAR decrypts, checks setup ID and identifier, and signs `SarSetupResponse`.
6. WT signs a wrapper binding the same setup ID.
7. Boomlet verifies WT and SAR signatures, identifier, and setup ID.
8. Boomlet stores its local SAR response.
9. Boomlet computes and signs:

```text
setup_checkpoint =
  tagged_sha256(
    "Boomerang/setup_phase_checkpoint",
    canonical_encode(
      setup_instance_id,
      "sar_ready",
      setup_checkpoint
    )
  )
```

10. Every peer verifies identical signed `setup_checkpoint` values.

Peer-specific SAR responses are not `setup_checkpoint` inputs.

### 13.10 Boomletwo backup

1. Iso installs Boomletwo, which generates an identity keypair.
2. User gives Iso `milestone_block_collection`, `network`, `mnemonic`, `passphrase`, `static_doxing_data`, and `doxing_password` for backup authorization and sar_setup_response verification.
3. Iso reconstructs the normal key and signs:

```text
BoomletBackupRequest {
  backup_boomlet_pubkey,
  backup_normal_pubkey
}
```

4. The request omits `setup_instance_id` because Iso has not yet received authoritative active setup state.
5. Boomlet verifies normal-key authorization and target key.
6. Boomlet exports authenticated state. The encrypted state includes `setup_instance_id`.
7. Boomlet sends Iso:
   - encrypted backup state;
   - active Boomlet identity public key;
   - `boomerang_params`;
   - signed SAR response.
8. Iso requires `boomerang_params.milestone_blocks` to equal the supplied
   `MilestoneBlocks` value, reconstructs and verifies the descriptor from
   `boomerang_params.peer_ids` and those milestones, requires the active
   Boomlet identity public key to appear exactly once in
   `boomerang_params.peer_ids`,
   and verifies the signed SAR response content: signature, setup ID field
   against `boomerang_params.setup_instance_id`, derived identifier, static
   envelope hash, and static envelope IV from `static_doxing_data` and
   `doxing_password`. Iso does not need a retained `SarId` for this backup-time
   check; the SAR public key is the signer identity of `signed SAR response`.
9. Iso transfers the encrypted state and active Boomlet identity to Boomletwo without a separate setup-ID field. The one-time backup bootstrap context is defined in Section 9.6.
10. Boomletwo decrypts, verifies the embedded setup ID, imports the state, and signs `BackupDone`.
11. Boomlet verifies `BackupDone`, marks backup complete, and rejects another backup request for the same active state.
12. Boomlet computes and signs:

```text
setup_checkpoint =
  tagged_sha256(
    "Boomerang/setup_phase_checkpoint",
    canonical_encode(
      setup_instance_id,
      "backup_ready",
      setup_checkpoint
    )
  )
```

13. Every peer verifies identical signed `setup_checkpoint` values.
14. Boomlet persists `setup_checkpoint` as its local final `setup_checkpoint`.
15. Setup completion notices contain status only. They do not transmit the final checkpoint or duplicate the setup ID.

### 13.11 Setup success

Setup is complete only if:

- ST enrollment succeeded;
- all records and agreements verified;
- all peers derived the same setup ID and descriptor;
- local WT and SAR receipts verified;
- Boomletwo import and `BackupDone` verified;
- every peer verified the final `setup_checkpoint` signatures;
- Boomlet persisted `boomerang_params` and the final `setup_checkpoint`.

## 14. Withdrawal state machine

Boomlet withdrawal states are:

```text
IDLE
  -> REVIEWING_TX
  -> APPROVED
  -> COMMITTED
  -> DIGGING
  -> READY_TO_SIGN
  -> SIGNING
  -> SIGNATURE_EXPORTED
  -> IDLE
```

Any invalid signature, envelope, nonce, setup ID, transaction ID, withdrawal ID,
sequence, height relation, or state transition returns the relevant Section 18
failure class and stalls the active ceremony. A stalled ceremony stops advancing
but remains bound to its active setup, withdrawal identifiers, transcript, and
replay state until a valid retry or recovery input is accepted, or until the
user or operator explicitly abandons it.

Withdrawal uses two IDs. The initiator-created `withdrawal_id` binds the setup, transaction, initiator identity, and initiator approval nonce after initiator review and during approval fan-out. After all peer approvals are verified, `approved_withdrawal_id` binds the exact unanimous approval set and identifies every following commitment, duress, ping, pong, reached-ping, signing, export, and replay scope.
`initiator` and `non-initiator` are withdrawal roles. Any active setup peer may
be the initiator; active setup peer order remains the order of
`peer_ids_collection`.

## 15. Withdrawal protocol

Every withdrawal identity signature is a `SignedMessage` produced by
`sign_message(private_key, domain, content)` and verified with
`verify_signature(expected_pubkey, expected_domain, message_signed_by_signer)`.
Withdrawal diagrams and implementation notes use the following domains:

| Signed content | Domain |
| --- | --- |
| ST nonce-bound transaction review object | `"Boomerang/withdrawal/tx_review_approval"` |
| `TxApproval` | `"Boomerang/withdrawal/tx_approval"` |
| `WtTxApproval` | `"Boomerang/withdrawal/wt_tx_approval"` |
| non-initiator approval-set attestation | `"Boomerang/withdrawal/approval_set_attestation"` |
| `TxCommit` | `"Boomerang/withdrawal/tx_commit"` |
| `PaddedMessage{content = signed TxCommit, padding = duress_placeholder}` | `"Boomerang/withdrawal/tx_commit_envelope"` |
| WT signature acknowledging a peer `TxCommit` | `"Boomerang/withdrawal/wt_tx_commit_ack"` |
| SAR signature over an encrypted `duress_placeholder` envelope | `"Boomerang/withdrawal/sar_placeholder_response"` |
| `Ping` | `"Boomerang/withdrawal/ping"` |
| `PaddedMessage{content = signed Ping, padding = duress_placeholder}` | `"Boomerang/withdrawal/ping_envelope"` |
| `Pong` | `"Boomerang/withdrawal/pong"` |

### 15.1 Preconditions

Withdrawal may begin only if:

- Boomlet has a locally stored final `setup_checkpoint`;
- selected inputs are controlled by the Boomerang descriptor;
- current height is at least `milestone_block_0`;
- the unsigned transaction is satisfiable under the 5-of-5 Boomerang branch;
- no other withdrawal ceremony is active;
- fallback-path spending is not being presented as Boomerang spending.

The user authorization model requires the User to know, or have an independent
tool for deriving, the `tx_id` of the intended transaction contents before
approving ST's display. ST is a trusted `tx_id` confirmation device, not the
transaction semantic renderer.

### 15.2 Initiator review

`tx_id` is the Bitcoin transaction identifier derived from the unsigned
transaction.

1. User supplies a PSBT to Niso.
2. Niso validates syntax, inputs, outputs, fees, descriptor membership, sighash policy, and milestone eligibility.
3. Niso sends PSBT and local block height to Boomlet.
4. Boomlet derives `tx_id`, creates fresh `st_preview_nonce`, stores the outstanding `{tx_id, st_preview_nonce}` review state, and uses that nonce for the ST freshness check.
5. Boomlet encrypts the nonce-bound `{tx_id}` object for ST.
6. ST displays `tx_id`.
7. User independently verifies that the displayed `tx_id` is the `tx_id` of the intended transaction contents and approves the `tx_id`.
8. ST signs the exact nonce-bound object and encrypts it to Boomlet.
9. Boomlet verifies signature, tx ID, nonce, and outstanding state.

### 15.3 Initiator approval and PSBT distribution

After successful initiator review, Boomlet creates a fresh `initiator_approval_nonce`, computes `withdrawal_id`, and signs:

```text
initiator_approval_nonce := fresh 32 bytes

withdrawal_id =
  tagged_sha256(
    "Boomerang/withdrawal_id",
    canonical_encode(
      setup_instance_id,
      tx_id,
      initiator_boomlet_identity_pubkey,
      initiator_approval_nonce
    )
  )

TxApproval {
  withdrawal_id,
  approval_nonce = initiator_approval_nonce,
  event_block_height
}
```

It encrypts the approval for WT and encrypts the PSBT separately for every other Boomlet. The per-recipient envelope binds sender, recipient, and `withdrawal_id`; the relay message carries `withdrawal_id` outside the encrypted approval so WT can select the correct authenticated context before decrypting. The PSBT lets peers derive `tx_id` locally.

WT verifies the initiator approval and signs `WtTxApproval`. WT then sends each non-initiator:

- WT approval;
- initiator approval;
- PSBT envelope addressed to that peer.

### 15.4 Non-initiator review

Before forwarding the PSBT envelope to Boomlet, each non-initiator Niso verifies
the visible approval state:

- WT and initiator signatures;
- initiator membership;
- `withdrawal_id` equality between the initiator approval and WT approval;
- block-height freshness;
- milestone eligibility.

Each non-initiator Boomlet verifies the same visible approval state and, during
authenticated decryption of the PSBT envelope, additionally verifies:

- PSBT envelope sender and recipient;
- reconstructed `withdrawal_id` equals `tagged_sha256("Boomerang/withdrawal_id", canonical_encode(setup_instance_id, psbt.derive_tx_id(), initiator approval signer identity key, initiator approval nonce))`.

Boomlet decrypts the PSBT and returns it to Niso after these checks. Niso verifies
the reconstructed `withdrawal_id` from the PSBT before displaying the complete
transaction to User. After user approval, Boomlet performs the same nonce-bound ST tx-ID review and signs its own `TxApproval` with a fresh peer `approval_nonce` and the initiator's `withdrawal_id`. Non-initiator approval relay messages also carry `withdrawal_id` outside the encrypted approval for context selection. Non-initiator approvals do not repeat `tx_id`; peers recover the approving identity from the signed-message wrapper and recover the transaction binding through the initiator's reconstructable `withdrawal_id`.

WT collects one valid approval from every peer and sorts the approvals in active setup peer order:

```text
ordered_peer_tx_approvals :=
  WT-sorted Collection<peer_i_tx_approval_signed_by_boomlet_i> [0 <= i <= 4]
  in active setup peer order, where ordered_peer_tx_approvals[i]
  is signed by peer_ids_collection[i].boomlet_identity_pubkey

ordered_non_initiator_peer_tx_approvals :=
  ordered_peer_tx_approvals with the initiator's approval omitted
```

Receivers verify the WT-supplied ordering before hashing: the collection MUST contain exactly one approval per expected active setup peer, no missing approvals, no duplicates, no wrong signer, no wrong `withdrawal_id`, and no ordering mismatch. Non-initiator receivers that receive `ordered_non_initiator_peer_tx_approvals` reconstruct `ordered_peer_tx_approvals` by inserting the stored initiator approval at the initiator's active setup peer position before computing the approved ID. No peer may commit before it has verified unanimous approval for one reconstructed `withdrawal_id` in the active setup. Approval-collection messages carry the signed approvals; every receiver computes the ID locally after verification. After verification, every participant computes:

```text
approved_withdrawal_id =
  tagged_sha256(
    "Boomerang/approved_withdrawal_id",
    canonical_encode(
      withdrawal_id,
      ordered_peer_tx_approvals
    )
  )
```

Before WT treats the non-initiator approval phase as complete, each non-initiator Boomlet MUST attest to the approval set it accepted. The Boomlet computes the fingerprint itself from the verified canonical approval set and WT approval; it MUST NOT sign a fingerprint supplied by Niso or any other host:

```text
approval_set_attestation_fingerprint :=
  tagged_sha256(
    "Boomerang/withdrawal/approval_set_attestation_fingerprint",
    canonical_encode(
    ordered_peer_tx_approvals,
    wt_tx_approval_signed_by_wt
    )
  )

approval_set_attestation_fingerprint_signed_by_boomlet_i :=
  sign_message(
    boomlet_i_identity_privkey,
    "Boomerang/withdrawal/approval_set_attestation",
    approval_set_attestation_fingerprint
  )
  [1 <= i <= 4]
```

WT MUST recompute `approval_set_attestation_fingerprint` from its accepted `ordered_peer_tx_approvals` and `wt_tx_approval_signed_by_wt`, then verify exactly one valid `approval_set_attestation_fingerprint_signed_by_boomlet_i` from each non-initiator Boomlet before advancing the withdrawal beyond approval collection. Each signed content value MUST equal the recomputed fingerprint. The attestation proves to WT that the non-initiator Boomlet verified the WT-supplied ordered approval set, WT approval, signer identities, freshness checks, and locally computed `approved_withdrawal_id`. This attestation is a synchronization and accountability barrier before commit/SAR processing; it is separate from the later commit signature, which binds a peer's funds-movement commitment to `approved_withdrawal_id` after this barrier.

### 15.5 Initial duress check and commitment

Each peer performs the duress challenge defined in Section 16.

Each Boomlet constructs a fresh `duress_placeholder`, then signs:

```text
TxCommit {
  approved_withdrawal_id,
  event_block_height
}
```

The signed commit and placeholder are wrapped as
`PaddedMessage{content = signed TxCommit, padding = duress_placeholder}`,
signed as one outer object, and encrypted for WT. WT:

1. authenticates and decrypts the outer object;
2. verifies the inner commit;
3. forwards the placeholder to the peer's setup-bound SAR;
4. waits for a valid encrypted SAR placeholder acknowledgment;
5. signs the peer commit;
6. distributes the complete commit collection and each peer's own encrypted SAR placeholder acknowledgment.

Every Boomlet verifies all commits and its exact encrypted SAR placeholder acknowledgment before entering `DIGGING`.

### 15.6 Digging initialization

On entering `DIGGING`, Boomlet sets:

```text
mystery =
  random_integer(
    MIN_TRIES_FOR_DIGGING_GAME_IN_BLOCKS,
    MAX_TRIES_FOR_DIGGING_GAME_IN_BLOCKS
  )
counter = 0
ping_seq_num = 0
reached_mystery_flag = false
reached_peers = empty
last_seen_block = niso_i_event_block_height
```

`mystery` is the fresh secret Boomlet threshold for this withdrawal ceremony's
digging progress. It remains private to Boomlet and MUST be erased with the rest of the active withdrawal state after export,
abort, or unrecoverable failure.
`counter` is the successful digging-game progress count.
`niso_i_event_block_height` is the latest Niso-supplied block height accepted
at `DIGGING` entry after the surrounding commit/SAR freshness checks. Boomlet
does not obtain an independent chain height for this initialization.

### 15.7 Ping

For each round, Boomlet signs:

```text
Ping {
  approved_withdrawal_id,
  last_seen_block,
  ping_seq_num,
  reached_mystery_flag
}
```

Boomlet attaches a newly encrypted placeholder, signs the combined object, encrypts it for WT, and increments `ping_seq_num` for the next ping.
Newly encrypted means a fresh `CbcCmacEnvelope` with a fresh IV over the current `duress_placeholder_plaintext`; the plaintext may be unchanged when no new duress check ran, but the encrypted placeholder envelope MUST NOT be reused across pings.
The combined object is
`PaddedMessage{content = signed Ping, padding = duress_placeholder}`.

WT verifies:

- both signatures;
- approved withdrawal ID;
- strict sequence increase;
- allowed height range;
- monotonic reached flag.

WT forwards every placeholder to SAR and obtains an encrypted SAR placeholder acknowledgment before using the ping in a pong.

### 15.8 Pong

After receiving valid current pings, WT waits until the minimum block distance is satisfied and signs:

```text
Pong {
  approved_withdrawal_id,
  event_block_height,
  prev_pings
}
```

`prev_pings` is recipient-specific and complete: for peer `i`, WT includes the
signed pings from every active peer `j != i`, ordered by `peer_ids_collection`
with peer `i` omitted. WT encrypts a recipient-specific pong for each Boomlet
and includes that peer's encrypted SAR placeholder acknowledgment.

Each Boomlet verifies:

- WT signature and envelope;
- approved withdrawal ID;
- `event_block_height` freshness;
- `prev_pings` contains exactly one signed ping from every active peer `j != i`;
- included peer ping sequence monotonicity;
- included peer ping reached-flag monotonicity;
- its own encrypted SAR placeholder acknowledgment.

### 15.9 Counter advancement

Boomlet increments `counter` only when:

- the pong is valid for the active ceremony;
- `niso_i_event_block_height` is strictly greater than the Boomlet's current
  `last_seen_block`, so the local chain view has advanced since the previous
  accepted ping;
- each included previous peer ping from every active peer `j != i` satisfies:

```text
prev_ping_j.last_seen_block >=
  niso_i_event_block_height -
  TOLERANCE_IN_BLOCKS_FROM_CREATING_PING_BY_OTHER_PEERS_TO_REVIEWING_THE_PING_IN_PEER_BOOMLET

prev_ping_j.last_seen_block <= niso_i_event_block_height
```

Reached peers' pings remain eligible for this freshness predicate. The reached
flag is used only for monotonicity checks and for WT's final all-peers-reached
termination condition; it MUST NOT make an otherwise valid current peer ping
ineligible for another Boomlet's counter advancement.

- no local height decrease, WT height decrease, sequence regression, or
  material RPC/WT chain-view disagreement is active.

After successful advancement:

```text
previous_last_seen_block = last_seen_block
counter = counter + 1

last_seen_block =
  min(
    niso_i_event_block_height,
    previous_last_seen_block +
      JUMP_IN_BLOCKS_IF_LAST_SEEN_BLOCK_LAGS_BEHIND_NISO_EVENT_BLOCK_HEIGHT_IN_BOOMLET
  )
```

`last_seen_block` MUST be monotonic within the ceremony. `ping_seq_num`,
`approved_withdrawal_id`, and the active setup/session binding remain part of
the ping and pong validation context; a pong or peer ping from another
withdrawal ceremony, setup instance, or earlier sequence MUST NOT advance the
counter.

If `counter >= mystery`, Boomlet sets `reached_mystery_flag = true`. It
MUST never revert that flag during the ceremony. A Boomlet that has reached its
mystery MUST continue the ping/pong loop, including fresh pings and
duress-placeholder handling, until WT distributes a valid
`reached_pings_collection`; reaching locally is not a terminal digging state.

Any detected local height decrease, WT height decrease, or material RPC/WT
disagreement returns `CHAIN_VIEW_UNSAFE` and stalls the active Boomerang
ceremony.

### 15.10 Repeated duress checks

At each round Boomlet draws an unbiased value for the configured interval. When the draw selects a check, Boomlet runs the Section 16 challenge before creating its next placeholder. 

### 15.11 Reached collection

WT terminates digging only after it has one valid current ping with
`reached_mystery_flag = true` from every peer. Until that condition holds, WT
continues accepting and forwarding valid pings and pongs for peers that have
already reached, so their true reached flags remain available to peers that
have not yet reached. It distributes the signed `reached_pings_collection`.

Niso and Boomlet independently verify all five pings, approved withdrawal IDs, signatures, sequences, and reached flags.

### 15.12 PSBT hydration

Niso may add signing-support metadata to the PSBT, including UTXO data, scripts, derivation paths, Taproot metadata, and non-semantic proprietary fields.
For Boomerang Taproot key-path inputs, the committed sighash policy is
`SIGHASH_DEFAULT` for every Boomerang input; PSBTs MUST NOT request
`ANYONECANPAY`, `NONE`, or `SINGLE` variants.

Hydration MUST NOT change:

- unsigned transaction version or locktime;
- input outpoints or sequence numbers;
- output scripts or values;
- input or output ordering;
- committed sighash policy;
- the derived `tx_id`.

Boomlet MUST revalidate descriptor membership, transaction semantics, `tx_id`, and the reached collection before allowing signing.
Iso has no durable setup or withdrawal state at this ceremony boundary; it
MUST reconstruct the normal key and verify only the local signing package it is
given: the PSBT's internal consistency, the supplied descriptor's ability to
describe the inputs it is asked to sign, and the MuSig2 aggregate key formed by
the reconstructed normal public key and Boomlet's supplied public share. Any
failed local signing-package check returns the relevant Section 18 failure class
and stalls the ceremony, unless the failure indicates nonce reuse, session
confusion, or another condition where continuing could expose signing secrets.
In that case Boomlet and Iso MUST erase session secrets immediately and require
explicit abandonment before any new ceremony can begin.

### 15.13 MuSig2 signing

1. User moves Boomlet to Iso.
2. Iso reconstructs the normal key.
3. Boomlet provides PSBT, descriptor, public share, and fresh public nonce.
4. Iso verifies the local signing package: PSBT consistency, descriptor
   membership for the inputs it is asked to sign, and the MuSig2 aggregate key
   formed from its reconstructed normal public key and Boomlet's public share.
5. Iso creates its MuSig2 nonce and partial signature.
6. Boomlet verifies the session, produces its partial signature, and completes the peer's aggregate signature according to BIP327.
7. Iso and Boomlet retain the signed PSBT fragment until export.

Nonce material MUST be unique to the session and erased after use.

### 15.14 Export, aggregation, and reset

1. User returns Boomlet to Niso.
2. Boomlet exports the signed PSBT fragment.
3. Boomlet clears active withdrawal state.
4. Niso sends the fragment to WT.
5. WT aggregates all peer fragments, verifies the complete transaction, and broadcasts it.
6. The broadcast transaction MUST have the `tx_id` committed by the reconstructed `withdrawal_id` and the approved withdrawal approval set.

## 16. Duress protocol

### 16.1 Consent set

Each ST maps duress challenge integers through `DURESS_DISPLAY_VOCABULARY`.
Every ST under the same `PROTOCOL_VERSION` MUST use the exact same ordered
193-entry vocabulary for consent enrollment and later duress challenges.

The user selects five distinct countries. Order is irrelevant. The resulting
`duress_consent_set` is stored only in Boomlet and memorized by User.

### 16.2 Challenge

1. Boomlet generates a permutation of integers `1..193` and a fresh `duress_check_nonce`.
2. Boomlet constructs `MessageWithNonce{content: duress_check_space, nonce: duress_check_nonce}`, stores the outstanding `{duress_check_nonce, duress_check_space, phase}`, and encrypts the nonce-bound list for ST.

```text
duress_check_nonce := fresh 32 bytes from Boomlet

duress_check_space_with_nonce =
  MessageWithNonce {
    content = duress_check_space,
    nonce = duress_check_nonce
  }
```

3. ST maps the challenge through `DURESS_DISPLAY_VOCABULARY`, creates five independently shuffled display copies, and stores display-to-original-index maps.
4. User selects one country from each column.
5. ST returns five original-list indices with the exact nonce.
6. Boomlet rejects no outstanding duress check, wrong phase, duplicate response, nonce mismatch, wrong count, duplicate indices, or out-of-range indices.
7. Boomlet resolves the indices to integers and compares the unordered set with `duress_consent_set`.

Equality means safe. Any other valid five-element set means duress.

### 16.3 Placeholder

`duress_placeholder` is a SAR-encrypted payload carrying either zeros or
`doxing_key_for_sar`.

```text
placeholder_plaintext =
  zero_bytes_32              if safe
  doxing_key_for_sar         if duress
```

Boomlet encrypts the plaintext for the setup-bound SAR using Boomlet-to-SAR
channel keys and a fresh CBC-CMAC envelope with context:

```text
canonical_encode("withdrawal_duress_placeholder", approved_withdrawal_id)
```

The channel keys bind protocol version and the Boomlet and setup-bound SAR
identities. The placeholder context binds the withdrawal message type and
approved withdrawal ID. Because `approved_withdrawal_id` includes
`withdrawal_id`, and `withdrawal_id` includes `setup_instance_id`, this single
scope binds the placeholder to the active setup session and prevents
cross-session replay.

The placeholder MUST be present on every duress-bearing commitment or ping path. Safe and duress cases use identical message types, routing, acknowledgment requirements, and retry behavior.

### 16.4 SAR processing

SAR authenticates and decrypts the placeholder:

- 32 zero bytes means no duress;
- a 32-byte value whose derived identifier exists means duress;
- any other value is malformed.

For duress, if `(approved_withdrawal_id, boomlet_identity_pubkey,
duress_placeholder.iv)` has not been saved, SAR derives the identifier,
retrieves rescue-data envelopes, decrypts them, saves that tuple, and begins
its external response procedure.

For every valid safe or duress placeholder, SAR signs the exact encrypted
placeholder envelope it received and encrypts that signed message for the
Boomlet:

```text
duress_placeholder_signed_by_sar =
  sign_message(
    sar_private_key,
    "Boomerang/withdrawal/sar_placeholder_response",
    duress_placeholder
  )

duress_placeholder_signed_by_sar_encrypted_by_sar_for_boomlet_i =
  cbc_cmac_encrypt(
    keys = channel_keys(
      sar_private_key,
      "sar",
      boomlet_i_identity_pubkey,
      "boomlet",
      sender_public_key = sar_pubkey,
      receiver_public_key = boomlet_i_identity_pubkey
    ),
    context = canonical_encode(
      "withdrawal_sar_placeholder_response",
      approved_withdrawal_id
    ),
    content = duress_placeholder_signed_by_sar
  )
```

The acknowledgment MUST NOT contain a status, duress flag, placeholder
plaintext, or plaintext hash in any WT-visible field. Valid safe and duress
cases MUST produce the same response type, size class, routing, retry behavior,
acknowledgment timing class, failure behavior, and externally observable
acknowledgment behavior. Boomlet decrypts its
acknowledgment, verifies the SAR signature with domain
`"Boomerang/withdrawal/sar_placeholder_response"`, and requires the signed
content to equal byte-for-byte the `duress_placeholder` envelope it sent.

### 16.5 Duress observability contract

Safe and duress placeholder handling MUST be indistinguishable to WT, Niso,
Boomlet before decryption of the SAR acknowledgment, network observers, and any
coercer who can observe protocol messages, retry timing, status fields, logs,
or metrics exposed by WT or SAR.

For valid safe and duress placeholders:

- WT-to-SAR forwarding, SAR acknowledgment, WT-to-Boomlet delivery, retries,
  retry timing, retry count, queue placement, operator-visible status, and
  final externally visible failure behavior MUST be driven only by the
  authenticated placeholder instance and MUST NOT depend on whether SAR
  classified the valid placeholder as safe or duress;
- SAR MUST produce the protocol acknowledgment within the same externally
  observable timing class for safe and duress placeholders;
- SAR MUST NOT delay the protocol acknowledgment until rescue-data retrieval,
  external response, operator review, law-enforcement contact, or any other
  duress-specific operational work has completed;
- SAR MUST durably record or queue duress activation before acknowledging a
  duress placeholder, but the subsequent rescue work MUST be asynchronous or
  otherwise timing-equalized so that it does not alter WT-visible protocol
  behavior;
- WT-visible and attacker-observable logs, metrics, status APIs, error pages,
  queue names, retry counters, and operator-visible protocol status MUST NOT
  reveal whether the valid placeholder was safe or duress.

Malformed placeholders, missing derived identifiers, context mismatches,
authentication failures, replay rejection, transport failures, SAR
unavailability, and acknowledgment delivery failures MUST map to a permitted
externally observable failure behavior without exposing a more detailed reason
to an attacker-observable interface. Implementations MAY retain detailed internal
diagnostics for security operations, but those diagnostics MUST be access
controlled and excluded from WT-visible, Niso-visible, and public protocol
surfaces.

### 16.6 Replay handling

SAR records duress activation by the tuple
`{approved_withdrawal_id, boomlet_identity_pubkey, duress_placeholder.iv}`.
The tuple is checked only after the placeholder envelope has been authenticated
and decrypted with the `"withdrawal_duress_placeholder"` context. Repeated
delivery under an existing valid safe or duress tuple is idempotent for SAR
activation and still returns the same externally indistinguishable
acknowledgment behavior. A mismatched context or unauthenticated placeholder
envelope MUST be rejected.
The same IV value under a different `approved_withdrawal_id` is a different
replay tuple; cross-session replay is rejected by CBC-CMAC context
authentication before this tuple check.

## 17. Replay resistance and binding

The protocol uses the narrowest replay mechanism appropriate to each scope:

- fresh challenge nonce for immediate ST request/response, including Boomlet-ST duress checks;
- signed `peer_setup_nonce` as setup-attempt entropy;
- deterministic `setup_instance_id` for setup-wide binding;
- chained `setup_checkpoint` phase labels for setup order;
- `withdrawal_id` for approval binding;
- `approved_withdrawal_id` for post-approval withdrawal-wide binding;
- monotonic `ping_seq_num` for digging rounds;
- block-height tolerances for delayed-message rejection;
- SAR placeholder replay memory;
- strict actor state transitions.

`peer_setup_nonce` MUST NOT be copied into messages already protected by a fresh challenge nonce. Peer-specific receipts MUST remain local prerequisites and MUST NOT enter common `setup_checkpoint` values.

## 18. Failure and recovery behavior

### 18.1 Failure classes

Implementations expose only these protocol-level classes:

- `INVALID_ENCODING`;
- `AUTHENTICATION_FAILED`;
- `CONTEXT_MISMATCH`;
- `REPLAY_OR_STALE`;
- `INVALID_STATE`;
- `PARAMETER_MISMATCH`;
- `CHAIN_VIEW_UNSAFE`;
- `USER_ABORT`;
- `SERVICE_UNAVAILABLE`.

Detailed cryptographic reasons MUST NOT be exposed across an attacker-observable interface.

### 18.2 Fail closed

On failure, the active Boomerang ceremony stops advancing and returns one of the
Section 18.1 failure classes. Fail-closed behavior does not automatically
authorize a fallback spend.

`stalled` means the active setup attempt or withdrawal ceremony remains bound to
its current setup IDs, withdrawal IDs, transcript, and replay state. It MUST NOT
advance until a valid retry or recovery input is accepted.

`abort` means explicit user or operator abandonment of the active attempt, or an
unrecoverable local session-secret risk such as MuSig2 nonce reuse or session
confusion. Aborting clears volatile active-attempt state but MUST NOT clear
long-lived setup state or replay memory. Restarting after an abort is a new
attempt and MUST satisfy the normal freshness requirements, including a fresh
`peer_setup_nonce` for setup and fresh MuSig2 nonce material for signing.

### 18.3 Retry

A retry MAY retransmit an identical authenticated object. It MUST NOT:

- reuse a challenge nonce for a different challenge;
- reuse an IV for different plaintext under the same key;
- change signed content while preserving a sequence number;
- create a new setup attempt without a fresh `peer_setup_nonce`;
- restart signing with reused MuSig2 nonce material.

For SAR placeholder acknowledgments, WT and SAR retries MUST be determined
only by the authenticated placeholder instance. Retry timing, retry count,
queue placement, operator-visible status, and final externally visible failure
class MUST NOT depend on whether SAR classified the valid placeholder as safe
or duress.

### 18.4 Service failure

WT or SAR unavailability returns `SERVICE_UNAVAILABLE` and stalls the Boomerang
path. Implementations MAY abort only after explicit user or operator
abandonment and later begin a new ceremony, but MUST NOT silently substitute an
unagreed service identity.

`OPEN ISSUE`: multi-WT failover, single-SAR replacement after setup, blame assignment, and interoperable timeout schedules are not yet defined.

### 18.5 Boomletwo

Backup import is defined, but activation, revocation, and prevention of concurrent active devices are not.

`OPEN ISSUE`: a recovery protocol MUST guarantee one active signing authority before Boomletwo can be used for production funds.

## 19. Security considerations

### 19.1 Coercion and forced determinism

Boomerang increases attacker uncertainty; it does not remove coercion. Loss of devices, peer refusal, late withdrawal, or waiting for fallback timelocks can restore predictability. Operators must roll funds into a fresh setup before deterministic fallback becomes an attractive coercion target.

### 19.2 Boomlet load

The chained `setup_checkpoint` hashes only setup ID, phase label, and predecessor. Peer-specific receipts remain local. Setup agreement reuses one signature object. The AES profile reuses one symmetric primitive for CBC, CMAC, and the SP 800-108 KDF. Implementations should cache derived keys transiently within an exchange, stream CMAC/CBC processing, reject oversized inputs before allocation, and avoid persisting recomputable context.

### 19.3 CBC requirements

Unauthenticated CBC is forbidden. CMAC verification precedes decryption and padding validation. Distinct keys, fresh IVs, full tags, uniform errors, and context binding are mandatory to prevent malleability and padding-oracle behavior.

### 19.4 Password entropy

`doxing_key` is a tagged SHA-256 derivation from a user-chosen `doxing_password`, not a memory-hard password KDF. Low-entropy or reused passwords permit offline guessing if rescue ciphertext leaks. The protocol does not require a fixed entropy threshold or another 12-word secret.

### 19.5 Hardware

The design assumes resistance to key extraction, fault injection, rollback, side channels, and unauthorized applet replacement. Java Card compatibility does not imply that every card satisfies these properties.

### 19.6 ST

A malicious ST can misdisplay transaction identifiers or alter user input. Pairing, physical inspection, controlled firmware, and an independent transaction-verification workflow remain necessary.

### 19.7 Niso and RPC

Niso is online and may be compromised. Boomlet revalidates transaction identity,
descriptor constraints, approved withdrawal state, and reached collection before
signing; Iso verifies only the local signing package it receives during the
isolated signing ceremony.

### 19.8 WT

WT can censor, delay, equivocate, or leak metadata. Signed peer objects prevent undetected content forgery but do not guarantee liveness or privacy.

### 19.9 SAR

SAR sees registration metadata and may eventually receive the decryption key. Legal authority, operational competence, jurisdiction, insider risk, and data retention are outside cryptographic guarantees.

### 19.10 Metadata

Tor does not eliminate timing, payment, endpoint, and service-correlation risk. Setup and withdrawal ceremonies are unusually structured and may be recognizable.

### 19.11 MuSig2

Nonce reuse or session confusion can expose private keys. BIP327 nonce and
session requirements are mandatory. Boomlet and Iso must erase session secrets
after completion, stall, or abort.

## 20. Privacy considerations

- WT should learn only peer pseudonyms, ceremony state, and data needed for coordination.
- SAR should store rescue ciphertext under pseudonymous identifiers.
- Phone should encrypt dynamic data before transmission.
- Payment mechanisms should avoid unnecessary identity linkage.
- Logs must exclude private keys, plaintext rescue data, consent sets, challenge answers, and decrypted PSBT secrets.
- Safe and duress traffic must remain externally indistinguishable in type, size class, routing, and acknowledgment behavior.

## 21. Conformance requirements

A conforming implementation MUST provide tests for:

- canonical encoding and rejection of alternate encodings;
- normal-key derivation, including BIP39 seed derivation, BIP32 path
  `m/52102'/coin_type'/account'/0/key_index`, child private key, and BIP340
  x-only `normal_pubkey` encoding;
- BIP340 domain-separated signatures;
- ECDH normalization;
- NIST AES-256-CMAC examples;
- SP 800-108 key derivation;
- CBC-CMAC encrypt-then-MAC positive and negative vectors;
- modified context, IV, ciphertext, and tag rejection;
- MAC-before-padding behavior;
- setup record ordering and setup ID derivation, including unsorted
  Niso-to-Boomlet records, duplicate Boomlet identity keys, missing or stale
  local signed records, and byte-for-byte unchanged setup IDs for correctly
  sorted input;
- `MilestoneBlocks` canonical encoding and rejection of missing fields,
  duplicate fields, list-style milestone encodings, non-increasing milestones,
  and setup-ID changes when any milestone field or order changes;
- descriptor construction using `milestone_block_0` through
  `milestone_block_5` for the six Taproot branches;
- `setup_checkpoint` equality despite different peer-local receipts;
- stale challenge nonce rejection;
- setup replay rejection;
- tx ID and setup ID mismatch rejection;
- ping sequence and reached-flag monotonicity;
- counter advancement requiring one fresh signed ping from every other active
  peer, including already reached peers, and rejecting missing, duplicate,
  stale, misordered, or wrong-signer peer pings;
- PSBT hydration constraints;
- MuSig2 nonce non-reuse;
- safe and duress placeholder flow equivalence, including identical
  WT-visible SAR acknowledgment shape, size class, timing class, retry
  schedule, and externally observable failure class;
- safe and duress replay equivalence, including identical externally
  indistinguishable acknowledgment behavior for repeated valid placeholders;
- malformed placeholder, missing identifier, context mismatch, authentication
  failure, SAR unavailability, and acknowledgment delivery failure mapping to
  the permitted externally observable failure behavior;
- slow or failed SAR rescue-data lookup and external response workflow not
  changing WT-visible acknowledgment timing, shape, routing, retry, or failure
  behavior for a valid duress placeholder;
- duress placeholder context binding, including rejection across a different
  `approved_withdrawal_id` or setup session and acceptance of the canonical
  context without ping sequence or commitment phase fields.

Protocol vectors MUST include exact canonical bytes, normal-key derivation
inputs and outputs, keys, IVs, ciphertexts, tags, signatures, identifiers, and
expected failure classes.


## 22. Open issues

The following work remains:

- select production mystery, freshness, and duress cadence parameters;
- define reorg and divergent-chain-view recovery;
- publish complete wire schema IDs and interoperability vectors;
- define ST prompt encoding and display-grid conformance requirements;
- define multi-WT failover and single-SAR replacement procedures;
- define Boomletwo activation, deactivation, revocation, and anti-clone behavior;
- define operational timeout and blame procedures;
- validate Java Card performance, endurance, and side-channel behavior across target cards;
- validate the full protocol with simulation, formal models, and independent cryptographic review.

These issues limit production deployment and must be resolved before a production profile is declared.

## 23. Normative references

- [RFC2119] "Key words for use in RFCs to Indicate Requirement Levels".
- [RFC8174] "Ambiguity of Uppercase vs Lowercase in RFC 2119 Key Words".
- [FIPS180-4] "Secure Hash Standard".
- [SP800-38A] NIST SP 800-38A, "Recommendation for Block Cipher Modes of Operation".
- [SP800-38B] NIST SP 800-38B, "Recommendation for Block Cipher Modes of Operation: The CMAC Mode for Authentication".
- [SP800-108] NIST SP 800-108 Revision 1, "Recommendation for Key Derivation Using Pseudorandom Functions".
- [SEC1] "Elliptic Curve Cryptography".
- [BIP32] "Hierarchical Deterministic Wallets".
- [BIP39] "Mnemonic code for generating deterministic keys".
- [BIP340] "Schnorr Signatures for secp256k1".
- [BIP341] "Taproot: SegWit version 1 spending rules".
- [BIP371] "Taproot Fields for PSBT".
- [BIP327] "MuSig2 for BIP340-compatible Multi-Signatures".
- [BIP174] "Partially Signed Bitcoin Transaction Format".
- [TOR-RENDEZVOUS] Tor Project, "Tor Rendezvous Specification, Version 3".
- [UN-MEMBER-STATES] United Nations, "Member States", https://www.un.org/en/about-us/member-states.

## Appendix A: Duress display vocabulary

`DURESS_DISPLAY_VOCABULARY` is fixed by `PROTOCOL_VERSION`. It contains the
following 193 display labels, indexed from 1 in the order shown:

1. Afghanistan
2. Albania
3. Algeria
4. Andorra
5. Angola
6. Antigua and Barbuda
7. Argentina
8. Armenia
9. Australia
10. Austria
11. Azerbaijan
12. Bahamas
13. Bahrain
14. Bangladesh
15. Barbados
16. Belarus
17. Belgium
18. Belize
19. Benin
20. Bhutan
21. Bolivia (Plurinational State of)
22. Bosnia and Herzegovina
23. Botswana
24. Brazil
25. Brunei Darussalam
26. Bulgaria
27. Burkina Faso
28. Burundi
29. Cabo Verde
30. Cambodia
31. Cameroon
32. Canada
33. Central African Republic
34. Chad
35. Chile
36. China
37. Colombia
38. Comoros
39. Congo
40. Costa Rica
41. Côte d'Ivoire
42. Croatia
43. Cuba
44. Cyprus
45. Czechia
46. Democratic People's Republic of Korea
47. Democratic Republic of the Congo
48. Denmark
49. Djibouti
50. Dominica
51. Dominican Republic
52. Ecuador
53. Egypt
54. El Salvador
55. Equatorial Guinea
56. Eritrea
57. Estonia
58. Eswatini
59. Ethiopia
60. Fiji
61. Finland
62. France
63. Gabon
64. Gambia
65. Georgia
66. Germany
67. Ghana
68. Greece
69. Grenada
70. Guatemala
71. Guinea
72. Guinea-Bissau
73. Guyana
74. Haiti
75. Honduras
76. Hungary
77. Iceland
78. India
79. Indonesia
80. Iran (Islamic Republic of)
81. Iraq
82. Ireland
83. Israel
84. Italy
85. Jamaica
86. Japan
87. Jordan
88. Kazakhstan
89. Kenya
90. Kiribati
91. Kuwait
92. Kyrgyzstan
93. Lao People's Democratic Republic
94. Latvia
95. Lebanon
96. Lesotho
97. Liberia
98. Libya
99. Liechtenstein
100. Lithuania
101. Luxembourg
102. Madagascar
103. Malawi
104. Malaysia
105. Maldives
106. Mali
107. Malta
108. Marshall Islands
109. Mauritania
110. Mauritius
111. Mexico
112. Micronesia (Federated States of)
113. Monaco
114. Mongolia
115. Montenegro
116. Morocco
117. Mozambique
118. Myanmar
119. Namibia
120. Nauru
121. Nepal
122. Netherlands (Kingdom of the)
123. New Zealand
124. Nicaragua
125. Niger
126. Nigeria
127. North Macedonia
128. Norway
129. Oman
130. Pakistan
131. Palau
132. Panama
133. Papua New Guinea
134. Paraguay
135. Peru
136. Philippines
137. Poland
138. Portugal
139. Qatar
140. Republic of Korea
141. Republic of Moldova
142. Romania
143. Russian Federation
144. Rwanda
145. Saint Kitts and Nevis
146. Saint Lucia
147. Saint Vincent and the Grenadines
148. Samoa
149. San Marino
150. Sao Tome and Principe
151. Saudi Arabia
152. Senegal
153. Serbia
154. Seychelles
155. Sierra Leone
156. Singapore
157. Slovakia
158. Slovenia
159. Solomon Islands
160. Somalia
161. South Africa
162. South Sudan
163. Spain
164. Sri Lanka
165. Sudan
166. Suriname
167. Sweden
168. Switzerland
169. Syrian Arab Republic
170. Tajikistan
171. Thailand
172. Timor-Leste
173. Togo
174. Tonga
175. Trinidad and Tobago
176. Tunisia
177. Türkiye
178. Turkmenistan
179. Tuvalu
180. Uganda
181. Ukraine
182. United Arab Emirates
183. United Kingdom of Great Britain and Northern Ireland
184. United Republic of Tanzania
185. United States of America
186. Uruguay
187. Uzbekistan
188. Vanuatu
189. Venezuela (Bolivarian Republic of)
190. Viet Nam
191. Yemen
192. Zambia
193. Zimbabwe

ST MUST use this exact ordered list for consent enrollment and later duress
challenges under the same `PROTOCOL_VERSION`. 
