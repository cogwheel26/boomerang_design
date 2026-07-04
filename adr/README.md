# Architecture Decision Records

This directory records protocol decisions whose rationale should survive diagram
and specification revisions.

`spec/SPEC.md` is the normative protocol specification. ADRs explain why a
decision was made, its trade-offs, and its implementation consequences; they do
not override the specification.

## Accepted Decisions

| ADR | Decision |
| --- | --- |
| [0001](0001-setup-replay-and-phase-checkpoints.md) | Derive one setup instance ID and use one compact chained setup checkpoint. |
| [0002](0002-java-card-cryptographic-profile.md) | Use AES-256-CBC/PKCS#7 with AES-CMAC and an AES-CMAC KDF. |
| [0003](0003-single-sar-per-peer.md) | Use exactly one setup-bound SAR per peer. |
| [0004](0004-per-channel-directional-keys.md) | Use one four-key directional schedule per endpoint pair. |

## Status Values

- `Proposed`: under active review and not yet normative.
- `Accepted`: reflected in the current protocol specification.
- `Superseded`: retained for history and linked to its replacement.
