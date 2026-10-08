# ADR 0010. Niso-Relayed Consent Rotation With ST Approval

- **Status:** Proposed
- **Recorded:** 2026-10-07

## Context

Boomlet and its designated inactive backup Boomletwo store the five-country
consent set. Their paired trusted ST device supplies user input and approval.
Reconstructing the normal key for consent rotation adds a mnemonic-handling
occasion and brings spending components together for maintenance. Iso receives
mnemonic, passphrase, and normal-key material
([SPEC §7.2](../spec/SPEC.md#72-iso-state)).
The normal key participates in final signing
([SPEC §15.13](../spec/SPEC.md#1513-musig2-signing)) and authorizes fallback branches
([SPEC §11.2](../spec/SPEC.md#112-taproot-policy)).

The mnemonic and passphrase determine the seed, from which the private key tree
can be reconstructed ([BIP39](https://bips.dev/39/), [BIP32](https://bips.dev/32/)).
Handling them during rotation creates another opportunity for capture or
accidental retention, with consequences beyond consent maintenance.

## Decision

Use Niso as an untrusted relay and authorize rotation with explicit signed ST
approval of the exact nonce-bound scope. Rotation requires no mnemonic,
passphrase, or normal private key.

During setup, the normal key certifies the setup, logical peer, both physical
devices' management keys, ST identity, and lifecycle generation. Boomlet,
Boomletwo, and ST retain that certificate and its public verification anchors.
Rotation verifies this fixed binding using public keys.

ST approval binds the retained pair certificate, predecessor consent epoch and
state sequence, next attempt sequence, and fresh review nonce. Both devices
independently verify the approval and their stored certificate. Source privately
binds the review to any current withdrawal and preserves it during rotation.
Niso transports encrypted messages and public review metadata.

ST approval permits consent rotation only within that fixed pair. Device
replacement, rebinding, signing, and Boomletwo activation retain their separate
requirements.

## Rationale

Consent maintenance can preserve the separation between the normal key and
Boomlet until an operation requiring both occurs. The existing trusted ST
provides explicit review and authenticated approval without exposing spending
credentials.

## Consequences

ST approval establishes trusted intent but provides less independent ownership
authentication than possession of the normal key. Someone controlling the paired
trusted devices and ST can perform unauthorized maintenance, including persistent
duress latching or history exhaustion. Approval also cannot prove freedom from
coercion.

Devices enforce scope, freshness, checkpoint admission, resource limits,
and durable two-phase recovery despite a malicious Niso. Rotation during an
active withdrawal is allowed during digging after commitment and in later phases,
preserving progress, signing history, and SAR obligations. Resumption requires a
fresh Ping's exact SAR acknowledgment.

Every rotation asks for the previous set. A valid wrong answer completes the
same flow, permanently latches duress within the setup, and transfers it to the
backup through encrypted two-phase commit with OR merging. Either classification
has the same observable behavior. Niso can interrupt delivery; uncertain
participants stay held.

## Rejected Alternatives

- **Iso plus fresh normal-key authorization:** adds an independent ownership
  credential but requires additional mnemonic access and spending-key handling
  for this maintenance operation.
- **Consent-set correctness as authorization:** the set may already be observed,
  and valid wrong answers must still complete rotation with persistent duress.
