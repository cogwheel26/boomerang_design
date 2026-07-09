# Boomerang Threat-Model Assumption Register And Derived Design Gaps

> Last change: 2026-07-09 | Change: Aligned assumptions and derived gaps with current `SPEC.md`;

## Table of Contents

- [Purpose](#purpose)
- [Corpus Reviewed](#corpus-reviewed)
  - [Core protocol and overview docs](#core-protocol-and-overview-docs)
  - [Canonical and supporting diagrams](#canonical-and-supporting-diagrams)
  - [Security WIP artifacts](#security-wip-artifacts)
  - [Hardware prototype material](#hardware-prototype-material)
  - [Files reviewed but not directly assumption-bearing](#files-reviewed-but-not-directly-assumption-bearing)
- [Method](#method)
- [Status Legend](#status-legend)
- [Source Legend](#source-legend)
- [High-Level Observations Before The Register](#high-level-observations-before-the-register)
- [Assumption Register](#assumption-register)
  - [A. Baseline Security Scope And Canonical Trust Boundaries](#a-baseline-security-scope-and-canonical-trust-boundaries)
  - [B. Bitcoin, Descriptor, And Timing Model](#b-bitcoin-descriptor-and-timing-model)
  - [C. Cryptography, Serialization, And Binding](#c-cryptography-serialization-and-binding)
  - [D. Boomlet And Boomletwo](#d-boomlet-and-boomletwo)
  - [E. Secure Terminal And Human Interface](#e-secure-terminal-and-human-interface)
  - [F. Iso, Niso, And Phone Environments](#f-iso-niso-and-phone-environments)
  - [G. Peers, Users, And Human Operations](#g-peers-users-and-human-operations)
  - [H. WT And SAR Service Assumptions](#h-wt-and-sar-service-assumptions)
  - [I. Network, Metadata, And Privacy](#i-network-metadata-and-privacy)
  - [J. Recovery, Uniqueness, And Design Evolution](#j-recovery-uniqueness-and-design-evolution)
- [Formal Threat-Model Boundaries Made Explicit By The TLA+ Spec](#formal-threat-model-boundaries-made-explicit-by-the-tla-spec)
  - [Formal Security Assumptions](#formal-security-assumptions)
  - [Additional Formal Security Assumptions Exposed By The Merged Withdrawal Model](#additional-formal-security-assumptions-exposed-by-the-merged-withdrawal-model)
  - [Formal Proof-Scope Limits That Narrow The Checked Security Claims](#formal-proof-scope-limits-that-narrow-the-checked-security-claims)
- [Derived Design Gaps](#derived-design-gaps)
- [Practical Reading Of The Register](#practical-reading-of-the-register)
- [Recommended Next Use Of This Document](#recommended-next-use-of-this-document)

## Purpose

This document is the repository's threat-model-oriented register. It collects the security-relevant assumptions and proof-scope limits that the current Boomerang design and formalization rely on, then derives a design-gaps table from those security-relevant boundaries only.

The goal is not to restate the protocol. The goal is to answer:

1. What must already be true for the current design's security story to hold?
2. Which of those assumptions are strong, underspecified, operational, or contradicted by the current prototype materials?
3. What concrete design gaps follow from those assumptions?

## Corpus Reviewed

The register below was compiled from the full repository as it exists today.

### Core protocol and overview docs

- `README.md`
- `spec/SPEC.md`
- `DEEPDIVE.md`
- `setup/README.md`
- `withdrawal/README.md`
- `duress_protection/README.md`
- `secure_terminal/README.md`
- `security_models/README.md`
- `security_models/forced_determinism.md`
- `adr/0001-setup-replay-and-phase-checkpoints.md`
- `adr/0002-java-card-cryptographic-profile.md`
- `adr/0003-single-sar-per-peer.md`
- `adr/0004-per-channel-directional-keys.md`

### Canonical and supporting diagrams

- `setup/setup_diagram_without_states.puml`
- `setup/setup_diagram_without_states.svg`
- `withdrawal/initiator_withdrawal_diagram_without_states.puml`
- `withdrawal/initiator_withdrawal_diagram_without_states.svg`
- `withdrawal/non_initiator_withdrawal_diagram_without_states.puml`
- `withdrawal/non_initiator_withdrawal_diagram_without_states.svg`
- `withdrawal/block_constraints.svg`
- `withdrawal/block_constraints.pdf`
- `duress_protection/duress_protection_setup_diagram.puml`
- `duress_protection/duress_protection_setup_diagram.svg`
- `duress_protection/duress_protection_withdrawal_diagram.puml`
- `duress_protection/duress_protection_withdrawal_diagram.svg`

### Security WIP artifacts

- `security_models/wips/README.md`
- `security_models/wips/setup/setup_data_integrity_diagram(wip).puml`
- `security_models/wips/setup/setup_integrity_checks(wip).ods`
- `security_models/wips/withdrawal/withdrawal_integrity_checks(wip).ods`
- `security_models/wips/withdrawal/withdrawal_freshness(wip).ods`
- `security_models/wips/leaked_data_analysis(wip).xlsx`
- `security_models/wips/duress_protection/README.md`

### Hardware prototype material

- `secure_terminal/ASX00031-datasheet.pdf`
- `secure_terminal/ABX00042-ABX00045-ABX00046-datasheet.pdf`

### Files reviewed but not directly assumption-bearing

- `security_models/wips/setup/README.md` is empty.
- `security_models/wips/withdrawal/README.md` is empty.
- `LICENSE` is legal metadata and adds no security-design assumptions.
- The SVG renders above mostly duplicate the corresponding PlantUML semantics, but were still checked for consistency.

## Method

An item was entered into the register when at least one of the following was true:

- the repo states the assumption directly;
- the security story cannot hold without the assumption;
- a WIP integrity/freshness artifact shows the protocol is relying on that assumption transitively;
- the prototype hardware material shows tension between the desired trust model and the currently named parts.

## Status Legend

- `Explicit`: stated directly in the repo.
- `Implicit`: necessary for the design to work, but not stated as a first-class assumption.
- `Open/WIP`: acknowledged in the repo as unresolved, deferred, or ancillary.
- `Resolved`: closed by the cited specification or ADR work.
- `Prototype tension`: the repo assumes something stronger than the currently referenced prototype hardware or process obviously guarantees.

## Source Legend

- `R`: `README.md`
- `SPEC`: `spec/SPEC.md`
- `DD`: `DEEPDIVE.md`
- `SM`: `security_models/README.md`
- `FD`: `security_models/forced_determinism.md`
- `ADR`: `adr/*.md`
- `SU`: `setup/README.md`
- `WD`: `withdrawal/README.md`
- `DP`: `duress_protection/README.md`
- `ST`: `secure_terminal/README.md`
- `SP`: `setup/setup_diagram_without_states.puml`
- `WI`: `withdrawal/initiator_withdrawal_diagram_without_states.puml`
- `WN`: `withdrawal/non_initiator_withdrawal_diagram_without_states.puml`
- `DCS`: `duress_protection/duress_protection_setup_diagram.puml`
- `DCW`: `duress_protection/duress_protection_withdrawal_diagram.puml`
- `BD`: `withdrawal/block_constraints.{svg,pdf}`
- `WIP-SI`: `security_models/wips/setup/setup_integrity_checks(wip).ods`
- `WIP-SD`: `security_models/wips/setup/setup_data_integrity_diagram(wip).puml`
- `WIP-WI`: `security_models/wips/withdrawal/withdrawal_integrity_checks(wip).ods`
- `WIP-WF`: `security_models/wips/withdrawal/withdrawal_freshness(wip).ods`
- `WIP-LD`: `security_models/wips/leaked_data_analysis(wip).xlsx`
- `WIP-DP`: `security_models/wips/duress_protection/README.md`
- `HW-BB`: `secure_terminal/ASX00031-datasheet.pdf`
- `HW-H7`: `secure_terminal/ABX00042-ABX00045-ABX00046-datasheet.pdf`

## High-Level Observations Before The Register

- The design already recognizes that many of its most important security guarantees are assumption-heavy: Boomlet behavior, ST integrity, peer cooperation, SAR and WT availability, and user rollover discipline.
- The specification uses `setup_instance_id`, chained setup checkpoints, `withdrawal_id`, `approved_withdrawal_id`, directional channel contexts, approval-set attestations, and exact SAR placeholder acknowledgements to close several integrity and binding gaps.
- The WIP freshness sheet shows some messages with explicit freshness guarantors and some with no direct freshness guarantor or freshness inferred from broader context.
- The hardware materials for the ST prototype emphasize flexibility, bootloader/debug access, exposed connectors, and prototyping convenience. The ST design doc assumes a much more appliance-like trust model.
- The repository already knows several hard gaps: forced determinism, Boomletwo activation, ancillary procedures, jurisdictional rescue limits, and the lack of final parameter selection.

## Assumption Register

### A. Baseline Security Scope And Canonical Trust Boundaries

| ID | Assumption | Sources | If False | Status |
| --- | --- | --- | --- | --- |
| AR-01 | The current `SPEC.md`, Markdown docs, ADRs, and sequence diagrams are internally consistent enough to define one security-relevant setup and withdrawal meaning for the current deliverable. | `SPEC`, `R`, `DD`, `SU`, `WD`, `SP`, `WI`, `WN`, `ADR` | Different components or future implementations may satisfy different security semantics while all claiming to implement "Boomerang". | Explicit |
| AR-03 | The security story is centered on the current exactly five-peer, 5-of-5 Boomerang profile described in the docs. | `SPEC`, `R`, `DD`, `SM` | Claims about one honest peer preserving Boomerang guarantees would not generalize. | Explicit |
| AR-04 | The separate PoC and any future implementation will preserve the same trust boundaries and message semantics described here. | `R`, `DD` | The register would not describe the system that actually gets built. | Implicit |
| AR-05 | Security-critical properties deferred to ancillaries, implementation detail, or operator discipline can be postponed without invalidating the current-stage security story. | `DD`, `SM` | Real-world safety and integrity may depend on unresolved implementation and operating assumptions more than the current design narrative admits. | Open/WIP |

### B. Bitcoin, Descriptor, And Timing Model

| ID | Assumption | Sources | If False | Status |
| --- | --- | --- | --- | --- |
| AR-06 | Bitcoin consensus, timelocks, and Taproot spending conditions behave as modeled by the descriptor design. | `R`, `DD`, `SM` | Both non-deterministic and fallback security claims may be wrong. | Explicit |
| AR-07 | `milestone_block_collection` is well-formed, strictly ordered, and operationally sensible. | `SU`, `SP`, `SM` | Users can enter fallback too early, or funds can become awkwardly or prematurely spendable. | Implicit |
| AR-08 | Withdrawal only starts after `milestone_block_0`, and all parties agree on that fact. | `WD`, `WI`, `WN`, `DD` | Protocol state can diverge or enter unintended pre-milestone behavior. | Explicit |
| AR-09 | Users will roll funds into a new Boomerang setup before deterministic fallback makes coercion timing predictable. | `FD`, `R`, `DD` | Boomerang degrades into a known-timeline withdrawal system. | Explicit |
| AR-10 | Reorgs are shallow or rare enough that a "most work block height" view is a safe enough synchronization primitive in the current design. | `SM`, `WI`, `WN`, `BD` | Freshness checks, milestone gating, and counter progression can all be evaluated on stale or reversible chain state. | Open/WIP |
| AR-11 | Niso and WT obtain accurate enough block height and chain context from their configured Bitcoin node(s). | `R`, `SU`, `WD`, `SM` | A bad node can skew timing, approvals, and liveness decisions. | Implicit |
| AR-12 | Fee estimation and PSBT hydration remain viable even after a possibly long withdrawal ceremony. | `WD`, `DD` | A valid intent may become economically or practically unsignable by the time signing starts. | Implicit |
| AR-13 | The ping-pong "digging game" usually terminates before deterministic fallback if users start in time. | `R`, `DD`, `FD`, `BD` | The main coercion-resistance promise collapses into forced determinism. | Open/WIP |
| AR-14 | Freshness tolerances can be tuned to cover block irregularity, network delay, user sleep, time zones, and SAR/WT latency without breaking liveness. | `BD`, `DD`, `WIP-WF`, `WIP-WI` | Honest executions will fail freshness checks, or malicious delay becomes too easy. | Open/WIP |

### C. Cryptography, Serialization, And Binding

| ID | Assumption | Sources | If False | Status |
| --- | --- | --- | --- | --- |
| AR-15 | Schnorr, MuSig2, ECDH, tagged hashing, SP 800-108 CMAC KDF, AES-256-CBC/PKCS#7, and AES-CMAC encrypt-then-MAC are secure as specified and implemented. | `SPEC`, `R`, `DD`, `SU`, `WD`, `DP`, `ADR` | Core funds, identity, and duress guarantees fail. | Explicit |
| AR-16 | Every component serializes and interprets the same canonical message content identically. | `SPEC`, `SU`, `WD`, `SP`, `WI`, `WN` | Signatures, CMACs, and identifiers can validate over mismatched semantics, or peers can disagree about what was approved. | Implicit |
| AR-17 | RNG quality is sufficient across Boomlet, ST, WT, SAR, and supporting hardware. | `R`, `DD`, `DP`, `ST`, `HW-H7` | Mystery, nonces, keys, and duress spaces can be biased or predictable. | Explicit |
| AR-18 | Nonces, setup and withdrawal scope IDs, chained setup checkpoints, sequence numbers, freshness checks, and SAR replay tuples are sufficient replay protection for the current message set. | `SPEC`, `DP`, `WD`, `DD`, `WIP-WF`, `ADR` | Old approvals, checks, placeholders, or commitments may be replayed into new contexts. | Explicit |
| AR-19 | `tx_id`, `withdrawal_id`, `approved_withdrawal_id`, approval-set attestations, signing-package verification, and final transaction revalidation are strong enough to anchor transaction-authorization correctness throughout the ceremony. | `SPEC`, `WD`, `WI`, `WN`, `DD` | A participant may believe they are approving one spend while another spend is actually signed. | Explicit |
| AR-20 | Fresh CBC IVs, context-bound SAR placeholder envelopes, status-free acknowledgements, and timing/error discipline make safe placeholders and duress placeholders indistinguishable to WT and external observers within the specified protocol surface. | `SPEC`, `DP`, `WD`, `DCW` | WT or an observer can learn whether duress was signaled from ciphertext behavior, acknowledgement behavior, or service-visible side effects. | Explicit |
| AR-21 | `doxing_key_for_sar -> doxing_data_identifier` is unique enough operationally to locate the right setup-bound SAR record without ambiguity. | `SPEC`, `SU`, `DP`, `SM` | SAR may fail to rescue the right user or may treat malformed inputs incorrectly. | Implicit |

### D. Boomlet And Boomletwo

| ID | Assumption | Sources | If False | Status |
| --- | --- | --- | --- | --- |
| AR-22 | Boomlet private key shares and identity keys are truly non-exportable. | `R`, `SM`, `DD` | The Boomerang regime can be bypassed or cloned. | Explicit |
| AR-23 | Boomlet's `counter`, `mystery`, and reach-state cannot be read, reset, cloned, or externally accelerated. | `R`, `DD`, `FD`, `SM` | Non-determinism becomes knowable or controllable by an attacker. | Implicit |
| AR-24 | Boomlet faithfully enforces one-way state such as "reached mystery" and does not regress after a flag is set. | `WD`, `WI`, `WN` | Peers can be desynchronized or coerced into incorrect liveness behavior. | Implicit |
| AR-25 | Boomlet can preserve state for months of coordinated ping/pong updates and then safely clear withdrawal-specific state after signing. | `WD`, `DD` | The ceremony may fail midstream or leak stale state into later withdrawals. | Implicit |
| AR-26 | Java Card-class hardware can perform the required cryptography and state updates within practical time and endurance limits. | `DD`, `FD` | The protocol becomes too slow, too fragile, or impossible to execute as designed. | Open/WIP |
| AR-27 | Backing up Boomlet state without copying the active `mystery`, and requiring Boomletwo to generate its own mystery after authenticated import, is sufficient to preserve intended liveness and security properties before activation is defined. | `SPEC`, `SM`, `SU`, `DD` | The backup may either weaken non-determinism or fail to give useful recovery. | Implicit |
| AR-28 | Only one of Boomlet and Boomletwo will ever be active, even though activation/deactivation is not yet specified. | `R`, `SM`, `DD` | Duplicate active devices or confused ownership can undermine both safety and liveness. | Open/WIP |
| AR-29 | Losing both Boomlet and Boomletwo is rare enough that fallback-only recovery remains acceptable. | `FD`, `DD` | Funds protection depends too heavily on rare but catastrophic device loss patterns. | Implicit |
| AR-30 | Secure-element supply chain, lifecycle, and side-channel properties are acceptable for a Bitcoin custody system. | `R`, `DD`, `SM` | A hidden hardware weakness can destroy the central Boomerang guarantee. | Explicit |

### E. Secure Terminal And Human Interface

| ID | Assumption | Sources | If False | Status |
| --- | --- | --- | --- | --- |
| AR-31 | ST is the trusted UI for verification and duress input; Niso is not. | `R`, `DP`, `ST`, `SM` | Duress signaling and user verification reduce to whatever the online host shows. | Explicit |
| AR-32 | ST securely generates, stores, and uses its long-term keys. | `ST`, `DP`, `DCS` | An attacker can read or alter the ST-Boomlet channel. | Explicit |
| AR-33 | ST displays exact Boomlet-authored content and its joystick records exact user intent. | `ST`, `DP`, `DCW` | Users can be tricked into false safe or false duress outcomes. | Explicit |
| AR-34 | ST remains air-gapped except for the intended QR exchange path. | `R`, `ST`, `DP` | Malware-capable connectivity can directly exfiltrate consent-set or duress data. | Explicit |
| AR-35 | An attacker cannot practically observe both the ST display and the user's selection behavior well enough to learn the consent set under coercion. | `DP`, `ST` | Plausible deniability degrades, and attackers can demand the true safe response. | Explicit |
| AR-36 | Users can memorize the consent set and reliably reproduce it under stress, fatigue, or coercion. | `DP`, `SU`, `DCS` | False duress or false safe outcomes become common. | Implicit |
| AR-37 | One ST per peer is enough for ongoing operation, even though ST replacement is still ancillary. | `DP`, `DD` | ST loss or compromise becomes an operational dead end. | Open/WIP |
| AR-38 | A DIY Portenta-based ST can be made tamper-evident/tamper-resistant enough to satisfy the repo's trust model. | `ST`, `HW-BB`, `HW-H7` | The assumed trusted UI is only a prototype dev kit with insufficient hardening. | Prototype tension |
| AR-39 | Prototype attack surface exposed by bootloader, USB, JTAG, Ethernet, SD, camera, and other breakout/debug features can be controlled by build and ops choices. | `HW-BB`, `HW-H7`, `ST` | The proposed ST platform may remain much easier to tamper with than the security model assumes. | Prototype tension |

### F. Iso, Niso, And Phone Environments

| ID | Assumption | Sources | If False | Status |
| --- | --- | --- | --- | --- |
| AR-40 | Iso runs in a truly isolated and trusted environment. | `R`, `DD`, `SM`, `SU` | Normal keys, mnemonic material, and approval checks become host-compromise targets. | Explicit |
| AR-41 | User-provided entropy, mnemonic handling, and passphrase handling on Iso are safe and high quality. | `SU`, `DD`, `WIP-LD` | Normal key security collapses independently of Boomlet. | Implicit |
| AR-42 | Niso can be distrusted for duress integrity yet still relied on for transport, hydration, routing, and local coordination. | `R`, `WD`, `ST` | The protocol leaves an online component with more power than the threat model admits. | Implicit |
| AR-43 | Niso's RPC endpoint is honest, reachable, and configured correctly. | `R`, `SU`, `WD`, `SM` | Block height, satisfiability, and freshness decisions can be manipulated. | Implicit |
| AR-44 | Phone OS/app security is good enough for dynamic doxing collection and SAR registration. | `R`, `DD`, `SU`, `DP` | Rescue data can be stale, forged, leaked, or suppressed. | Explicit |
| AR-45 | Phone-to-SAR registration, payment, and sync cannot be silently redirected or spoofed in a way the user will miss. | `SU`, `WIP-SI` | The user can think they are covered while SAR never received valid rescue data. | Implicit |
| AR-46 | Users can safely shuttle Boomlet between Iso and Niso without plugging the wrong device into the wrong host or mixing peer hardware. | `SU`, `WD`, `DD` | Cross-device confusion can undermine both safety and liveness. | Implicit |
| AR-47 | Missing change procedures for Phone, Niso, and ST can be deferred to ancillaries without invalidating the current design. | `DD` | Operational device loss or replacement breaks the system before production readiness is even assessed. | Open/WIP |

### G. Peers, Users, And Human Operations

| ID | Assumption | Sources | If False | Status |
| --- | --- | --- | --- | --- |
| AR-48 | At least one honest peer exists in the N-of-N Boomerang regime. | `R`, `SM`, `DD` | The "one honest peer preserves the promise" argument disappears. | Explicit |
| AR-49 | Peers honestly exchange and verify peer IDs and Tor addresses out of band. | `R`, `SU`, `SP`, `SM` | Impersonation or routing attacks can be injected before Tor is even used. | Explicit |
| AR-50 | Users and peers meaningfully verify ordered peer setup records, WT order, milestone blocks, `setup_instance_id`, transaction identifiers, and peer data when prompted. | `SPEC`, `SU`, `WD`, `SP`, `WI`, `WN` | Human checks become ceremonial only, leaving host-mediated substitution attacks alive. | Implicit |
| AR-51 | Peers remain available across randomized delays, recurring duress checks, and long withdrawal timelines. | `DD`, `FD`, `BD` | Honest liveness fails under normal operational conditions. | Implicit |
| AR-52 | Non-cooperation is rare enough that N-of-N remains acceptable despite known liveness cost. | `R`, `FD`, `DD` | The system regularly falls back to deterministic recovery or deadlock. | Explicit |
| AR-53 | Peers will not exploit deterministic fallback once they can predict or wait out Boomerang timing. | `FD`, `DD` | The normal regime becomes an insider bypass path rather than only a liveness valve. | Implicit |
| AR-54 | Users will maintain safe backups, heed rollover timing, and follow operational guidance consistently. | `R`, `FD`, `DD` | Security rests on a discipline level that the design itself does not enforce. | Explicit |

### H. WT And SAR Service Assumptions

| ID | Assumption | Sources | If False | Status |
| --- | --- | --- | --- | --- |
| AR-55 | The one active WT stays available and responsive for the entire setup or withdrawal ceremony. | `SPEC`, `R`, `SM`, `WD`, `WIP-DP` | Coordination and counter progression stop even when peers are honest. | Explicit |
| AR-56 | WT signs only correct protocol statements and forwards messages without selective censorship or bias. | `WD`, `WI`, `WN`, `SM` | A non-custodial service can still force desynchronization or liveness failure. | Implicit |
| AR-57 | WT's block-height view is trustworthy enough to act as the protocol heartbeat. | `R`, `DD`, `SM`, `WD` | Freshness windows and progress rules rest on an attacker-controlled clock. | Explicit |
| AR-58 | WT redundancy, switching, and recovery can be designed later as ancillaries. | `SM`, `DD` | A single service dependency remains a critical current design weakness. | Open/WIP |
| AR-59 | SAR securely stores encrypted doxing data, identifiers, and related metadata over long periods. | `R`, `SM`, `SU`, `DP` | Off-chain safety data become a privacy or rescue failure point. | Implicit |
| AR-60 | Each setup-bound SAR reliably detects positive duress, suppresses duplicates by the specified replay tuple, and returns acknowledgements over the exact encrypted placeholder envelope that Boomlet can trust. | `SPEC`, `SM`, `WD`, `DP`, `DCW` | Positive duress may be missed, or Boomlet may continue under false delivery assumptions. | Implicit |
| AR-61 | SAR will be able to act effectively, lawfully, and in the relevant jurisdiction once duress occurs. | `R`, `DD`, `SM` | Duress signaling may work cryptographically while failing in the real world. | Explicit |
| AR-62 | Reputation and SAR operator selection are an acceptable control for WT and SAR social trust. | `DD`, `SM` | Operational trust becomes a hand-waved placeholder rather than a designed control. | Explicit |
| AR-63 | SAR will not become a later attacker after identity is revealed during a rescue event. | `DD`, `SM` | Duress rescue itself may create a future targeting or coercion channel. | Implicit |

### I. Network, Metadata, And Privacy

| ID | Assumption | Sources | If False | Status |
| --- | --- | --- | --- | --- |
| AR-64 | Tor provides enough reachability and anti-correlation benefit for peer, WT, and SAR communication. | `R`, `SM`, `SU` | Operators can be deanonymized or the protocol can be DoS'd more easily than assumed. | Explicit |
| AR-65 | Signed onion addresses are sufficient identity binding for peer communications. | `SU`, `SP`, `SM` | Attackers can redirect peer traffic despite signed address exchange. | Implicit |
| AR-66 | Metadata leakage to WT, SAR, phone infrastructure, and network observers is acceptable for the target threat model. | `R`, `SM`, `DD`, `WIP-LD` | The system may reduce coercion timing risk while increasing targeting risk. | Explicit |
| AR-67 | Static and dynamic doxing data remain confidential until a real duress event. | `SM`, `SU`, `DP`, `WIP-LD` | The rescue channel itself becomes a high-value doxing database. | Explicit |
| AR-68 | The WIP leaked-data analysis already captures the major sensitive-data inventory that matters for passive compromise. | `WIP-LD`, `SM` | Passive privacy exposure may be larger than the current model assumes. | Open/WIP |
| AR-69 | Direct Bitcoin node RPC access outside Tor does not create unacceptable integrity or targeting risk. | `R`, `SM`, `SU` | Node traffic becomes another deanonymization or chain-view manipulation vector. | Implicit |

### J. Recovery, Uniqueness, And Design Evolution

| ID | Assumption | Sources | If False | Status |
| --- | --- | --- | --- | --- |
| AR-70 | ~~Setup-instance uniqueness gaps can be fixed later without invalidating current setup security reasoning.~~ Setup-instance uniqueness is now a resolved historical assumption: the current design uses `peer_setup_nonce`, `setup_instance_id`, ST review, and chained setup checkpoints. | `SPEC`, `DD`, `SU`, `WIP-SD`, `ADR` | ~~Replay and cross-instance confusion may already be materially under-modeled.~~ Remaining risk is implementation conformance and evidence retention, not missing setup identity. | Resolved |
| AR-71 | Ancillary procedures can be deferred: WT switch, Boomletwo activation, Phone change, Niso change, ST change, SAR-set change, timeout handling, blame handling. | `DD`, `SM` | Realistic operations break long before the core withdrawal logic is reached. | Open/WIP |
| AR-72 | The protocol's complexity will not produce hidden failure modes beyond what later analysis can catch. | `R`, `DD`, `SM` | Emergent bugs and unsafe interactions may outpace informal reasoning. | Explicit |
| AR-73 | Dynamic simulation, threat-model completion, and later implementation work will eventually validate the timing and liveness claims. | `DD`, `SM` | The current security story may never become operationally defensible. | Open/WIP |
| AR-74 | Open parameter choices for `mystery`, intervals, and tolerances can be resolved without changing the core security story. | `SM`, `DD`, `FD`, `BD` | The promised deterrence/liveness balance may depend on values that do not actually exist. | Open/WIP |
| AR-75 | Using currently referenced prototype hardware with exposed prototyping/debug features does not invalidate the research conclusions being drawn today. | `ST`, `HW-BB`, `HW-H7` | Early conclusions about the trusted UI may rest on a platform that is materially weaker than assumed. | Prototype tension |
| AR-76 | Software build, update, deployment, and ordinary implementation hardening for Iso, Niso, ST, Boomlet, WT, and SAR are trustworthy enough for the current stage. | `SM`, `R`, `DD` | Malicious updates, compromised build pipelines, or ordinary service implementation flaws can bypass protocol-level guarantees even if the message design is sound. | Open/WIP |

## Formal Threat-Model Boundaries Made Explicit By The TLA+ Spec

This section records only the security-relevant boundaries that became explicit while writing the current withdrawal-focused TLA+ model in this repository. Some of them are genuine trust assumptions that the security story relies on. Some are proof-scope limits that narrow what the checked TLC results should be read as proving.

These `FM-*` items supplement rather than replace the main design assumptions above. When an `FM-*` item overlaps with an `AR-*` item, read it as the exact security boundary used by the current formalization.

Pure tractability choices, translation mechanics, and similar model-internal conveniences are intentionally not listed here unless they change the security meaning of the checked results.

### Formal Security Assumptions

- `FM-01`: principal identity binding is stable at the model boundary.
  The model assumes actions attributed to a peer, WT, or SAR really come from that principal.
  Why this matters: the `N-of-N` and one-honest-peer properties only mean what they should if named principals cannot be impersonated inside the modeled protocol.

- `FM-02`: honest approvals, commitments, and signatures are unforgeable.
  The model treats those security-relevant events as transitions that only the named peer can trigger.
  Why this matters: the checked withdrawal safety properties only mean what they should if protocol-authored messages cannot be forged inside the modeled boundary.

- `FM-03`: protected cryptographic payloads stay secret unless the protocol explicitly escalates them.
  The model idealizes the relevant privacy boundary: placeholder instances are opaque, and SAR learns actionable identity only after positive duress and escalation.
  Why this matters: the checked privacy boundary is perfect-cryptography style and does not cover WT telemetry, logs, timing, or transport metadata.

- `FM-04`: freshness evidence is trustworthy at the modeled level.
  The model abstracts freshness to `seen_block`, `blockHeight`, and `FreshnessWindow`, and the core model further compresses the many source-specific timing edges into a smaller set of proof-relevant freshness classes plus acceptance-time witness maps.
  Why this matters: it assumes those values are not attacker-forged within the modeled boundary, even though deep reorgs, split chain views, and compromised block oracles are not represented directly, and it also means the core proof is not an edge-by-edge replay of every asymmetrical timing constant in the diagrams.

- `FM-05`: mystery values remain hidden and unpredictable until protocol progress reveals them.
  The model represents per-peer `mystery` values as hidden local state and enforces all-mystery gating before readiness.
  Why this matters: the design promise that participants cannot know the exact signing moment in advance relies on this hidden-state assumption; the current TLA+ model captures the mechanism, not a full epistemic proof.

- `FM-07`: local trusted components faithfully capture approval and duress intent.
  The design-first model treats approval and duress as explicit protocol outcomes rather than modeling malware or UI compromise that fabricates or suppresses user intent.
  Why this matters: the SAR-escalation and deniability claims checked in the model assume the local security boundary behaves as intended.

- `FM-09`: replay resistance reduces to freshness plus single-use placeholder instances inside a sequential-session model.
  The model enforces freshness guards, single-use placeholder-instance replay memory at SAR, and reset-separated sequential sessions. It does not model concurrent sessions.
  Why this matters: the anti-replay claims do not cover concurrent multi-session deployment behavior.

- `FM-10`: fallback predicates are truthful, and fallback activation cannot be attacker-forced outside the modeled conditions.
  The formal model reduces fallback to hardware loss plus milestone gating and does not model a compromised device lying about loss or the unfinished Boomletwo activation ceremony.
  Why this matters: `FallbackOnlyAfterLossOrMilestone` is only as strong as the fidelity and non-spoofability of those triggering conditions.

### Additional Formal Security Assumptions Exposed By The Merged Withdrawal Model

These assumptions were made explicit while merging the narrow PlusCal withdrawal-core slice and the broader withdrawal-only microscope into one authoritative withdrawal model. They complement the existing `FM-*` items above; they do not supersede them.

- `FM-13`: the withdrawal proof starts after a correct setup-to-withdrawal handoff.
  The current authoritative model intentionally starts post-setup and assumes ST pairing, consent-set enrollment, and the relevant key relationships are already correct when the first withdrawal step occurs.
  Why this matters: the model does not itself prove that setup artifacts were generated correctly or transferred safely into withdrawal.

- `FM-14`: an authenticated withdrawal-session identifier exists across the ceremony.
  The model uses explicit `session_id` binding for initiator approval, peer approvals, commitments, pings, readiness, signing tickets, and reset-separated reuse prevention. Current `SPEC.md` resolves the design counterpart with `withdrawal_id` for approval fan-out and `approved_withdrawal_id` for every post-approval replay scope.
  Why this matters: ~~the design docs strongly imply this kind of binding, but they do not yet specify a canonical, authenticated session token or transcript object that carries it.~~ The remaining risk is implementation conformance between the formal `session_id` abstraction and the two concrete SPEC identifiers.

- `FM-15`: hydration and signing preserve the committed transaction intent in a way every honest peer can verify.
  The model includes an explicit non-initiator local PSBT-review gate, role-specific approval-window ordering around WT approval, and an explicit hydration step that must preserve the locked `tx_id`. `SPEC.md` adds descriptor membership, transaction semantics, reached-collection, signing-package, and final broadcast `tx_id` checks, while exact implementation test vectors and operator procedures remain outside the model.
  Why this matters: the model's transaction-tampering guarantees assume the concrete SPEC re-check rules are implemented faithfully and that `tx_id` continuity is paired with the specified signing and broadcast validation.

- `FM-16`: SAR acknowledgements are bound to the exact placeholder instance they acknowledge.
  The model lets progress depend on settling the latest commit or ping placeholder delivery before moving forward. `SPEC.md` uses SAR signatures over the exact encrypted `duress_placeholder` envelope and Boomlet verification that the signed content matches byte-for-byte.
  Why this matters: this remains a critical implementation invariant because a stale acknowledgement could otherwise satisfy progress guards while failing to prove real delivery of the current duress-bearing payload.

- `FM-17`: liveness claims rely on explicit fairness assumptions, not only on enabled transitions.
  The repository now carries a separate `SpecWithFairness` and liveness cfg for narrow service-progress properties, not a full honest-path completion theorem.
  Why this matters: claims like "fresh pending SAR acknowledgements are eventually delivered" or "loss eventually triggers fallback" do not follow from safety-only `Spec`, and the repo should not be read as already proving eventual approval completion, universal reach, all-signed, or eventual broadcast.

- `FM-18`: accepted freshness evidence is preserved and attributable enough to justify later security-sensitive transitions.
  The model assumes that once a principal accepts an approval, commit, ping, pong, or SAR acknowledgement as fresh, the security-relevant fact of that acceptance is not later confused with some other event or silently forgotten in a way that would permit replay or stale evidence reuse.
  Why this matters: the security story depends not just on checking freshness once, but on later protocol steps still being grounded in the right accepted evidence.

- `FM-19`: the model assumes exactly one SAR per peer.
  The canonical withdrawal model treats SAR as single per peer, with one acknowledgement stream and one replay-memory set per peer. `SPEC.md` and ADR 0003 define one selected SAR identity per peer and setup-bound SAR routing.
  Why this matters: the checked results no longer leave that part ambiguous, but they also do not prove any quorum, redundancy, or disagreement behavior because that is out of scope.

- `FM-22`: each security-relevant placeholder instance has a unique replay-relevant identity.
  The proof assumes that a commit/ping placeholder can be distinguished from stale prior placeholders well enough for replay suppression and acknowledgement binding to be meaningful. `SPEC.md` uses fresh `CbcCmacEnvelope` IVs, `approved_withdrawal_id` context binding, and SAR replay tuples `{approved_withdrawal_id, boomlet_identity_pubkey, duress_placeholder.iv}`.
  Why this matters: if "the current placeholder" cannot be identified unambiguously for security purposes in an implementation, then acknowledgement binding and replay suppression claims become much weaker than the model suggests.

- `FM-23`: SAR can enforce replay suppression for the relevant placeholder identity at least on a per-peer basis.
  The proof assumes SAR can recognize that the same security-relevant placeholder has already been seen for that peer and will not accept it again as fresh delivery evidence. `SPEC.md` requires SAR replay memory keyed by `{approved_withdrawal_id, boomlet_identity_pubkey, duress_placeholder.iv}` and idempotent repeated delivery under an existing valid tuple.
  Why this matters: without reliable replay suppression at SAR, stale placeholder traffic or stale acknowledgements could satisfy the modeled delivery guards without proving delivery of the current payload.

- `FM-28`: recurring duress cadence now follows the design’s modulo trigger, but the PRNG itself is still abstract.
  The core and wire models fire a repeated check only when an abstract bounded draw satisfies `draw % DURESS_CHECK_INTERVAL_IN_BLOCKS = 0`. The design corpus defines that modulo rule, but not one canonical PRNG seed, persistent state, entropy source, or cross-peer independence contract.
  Why this matters: the checked results now align with the documented cadence rule, but they still do not prove any implementation-specific RNG construction or bias-resistance story beyond the existing RNG assumptions.

### Formal Proof-Scope Limits That Narrow The Checked Security Claims

- `FM-06`: publicly observable behavior is approximated by an observable-envelope projection.
  The model uses `ObservableEnvelopeConsistentUnderPrivateDuress` to compare public message shape while hiding placeholder plaintext class and other private local state.
  Why this matters: timing leaks, payload lengths, UI behavior, transport metadata, and other side channels remain outside the current security proof boundary.

- `FM-08`: WT and SAR observe only the security-relevant knowledge modeled for them.
  The model gives WT and SAR only the state that appears in the formal variables and invariants, such as opaque placeholder instances, pending acknowledgements, replay memory, and escalation status.
  Why this matters: operational telemetry, metadata, logging, or implementation-specific side channels are not represented, so privacy conclusions remain narrowly scoped.

- `FM-11`: the current model does not include a full byzantine network attacker.
  Communication is abstracted into enabled protocol transitions rather than explicit message buffers with loss, duplication, censorship, or arbitrary reordering.
  Why this matters: the proven security properties are protocol-state guarantees under this abstraction, not a complete statement about hostile transport behavior.

- `FM-20`: signing and export are abstracted with a lightweight signing ticket rather than the full MuSig2 transcript.
  The model now binds hydration, signed-PSBT export, and broadcast to a common `SigningTicketFor(session_id, tx_id)` witness, while still omitting nonce and partial-signature details.
  Why this matters: the current proof covers the authorization and transcript-binding boundary around signing, not the full cryptographic correctness of the signing subprotocol.

- `FM-21`: deterministic fallback remains a boundary event, not a fully specified ceremony.
  The model can represent hardware loss, milestone-based fallback availability, fairness-backed fallback progress, and the fact that fallback must stay separate from boomerang signing, but it still does not specify how the deterministic spend is executed.
  Why this matters: the current result proves separation and scoped progress claims at the boundary, not the end-to-end security of the fallback procedure itself.

- `FM-24`: successful post-broadcast reset clears volatile withdrawal state before a later withdrawal session starts.
  The model supports sequential withdrawals in one run, but only by explicit reset after successful broadcast. Concurrent sessions are still outside the model.
  Why this matters: stale cross-session message acceptance is checked only for reset-separated sequential sessions; one active withdrawal at a time is still assumed.

- `FM-25`: ST/Boomlet nonce transcripts are modeled explicitly, but the challenge content remains symbolic rather than a literal country-grid/UI encoding.
  The model now carries explicit nonce-bound `tx_id` and duress transcript records and requires exact challenge-response agreement on `{sid, tx_id, peer, stage, seq, nonce}` before approval, commit, or recurring-check-dependent ping emission. It still abstracts the displayed challenge space to a Boolean `consent_match` outcome rather than the design's literal five-column country-set interaction.
  Why this matters: replay and phase-mixup resistance at the ST boundary are now represented directly, but UI-level ambiguity, country-grid encoding mistakes, and exact human-factor failure cases remain outside the checked proof surface.

- `FM-26`: end-to-end duress indistinguishability is modeled only at the message-envelope level, not at the timing/service-behavior level.
  The model checks that private duress choice does not alter the abstract public envelope shape at the modeled decision points, but it does not prove equal processing latency, equal error behavior, equal retry behavior, or equal total ceremony duration after duress is signaled. `SPEC.md` specifies equal WT-visible acknowledgement shape, retry, timing class, logging, metrics, and failure behavior for valid safe and duress placeholders.
  Why this matters: the TLA+ result supports only a narrower structural surrogate, so implementation and service audits must verify the broader operational indistinguishability contract in the SPEC.

## Derived Design Gaps

The gaps below are derived from the security-relevant register above. A gap is listed when one or more assumptions or proof-scope limits are:

- unresolved or explicitly deferred;
- operational rather than protocol-enforced;
- stronger than the available prototype evidence supports;
- necessary for safety but not concretely specified or tested.

| Gap ID | Derived From | Design Gap | Why It Exists Now | Resolution | Priority |
| --- | --- | --- | --- | --- | --- |
| DG-01 | `AR-10`, `AR-11`, `AR-14`, `AR-57`, `AR-69` | No explicit reorg and block-oracle policy | The protocol heavily relies on "most work block height", but the repo does not define reorg handling, node trust boundaries, or what to do on divergent chain views. |  | Critical |
| DG-02 | `AR-07`, `AR-09`, `AR-13`, `AR-14`, `AR-74` | No parameter-selection framework for milestones, mystery range, and freshness windows | The security story depends on the right timing constants existing, but the repo does not yet specify how to choose or validate them. |  | Critical |
| DG-03 | `AR-09`, `AR-13`, `AR-29`, `AR-52`, `AR-53`, `AR-54` | Forced determinism is still controlled mostly by user discipline and peer behavior | The repo explicitly acknowledges late start, device loss, and non-cooperation as collapse paths, but the mitigation is still "roll over in time and operate carefully." |  | Critical |
| DG-04 | `AR-27`, `AR-28`, `AR-71` | Boomletwo activation and anti-clone semantics are unspecified | Current `SPEC.md` defines authenticated backup import excluding active `mystery`, but the safe way to deactivate Boomlet and activate Boomletwo without creating duplicate authority is not yet designed. |  | Critical |
| DG-05 | `AR-18`, `AR-70` | ~~Setup uniqueness and anti-replay are incomplete~~ Setup uniqueness and anti-replay are preserved as a resolved historical gap | ~~The repo explicitly says some setup messages are not unique to a specific setup instance, which means replay resistance is not yet closed end-to-end.~~ Current `SPEC.md` defines `setup_instance_id`, `peer_setup_nonce`, and setup checkpoints. | Resolved in 96734855a35db6af7c6d8be06d72d452433bbc6b by `setup_instance_id`, `peer_setup_nonce`, and setup checkpoints. | High |
| DG-06 | `AR-15`, `AR-16`, `AR-17`, `AR-20`, `AR-21` | ~~The cryptographic profile is under-specified~~ Cryptographic implementation evidence remains incomplete | ~~The docs name primitives and flows, but not the final AEAD mode, KDF choices, transcript binding rules, canonical encodings, or test vectors needed for interoperable security.~~ Current `SPEC.md` fixes AES-256-CBC/PKCS#7, AES-CMAC encrypt-then-MAC, SP 800-108 CMAC KDF contexts, canonical bytes, and scope-specific binding. | Current `SPEC.md` resolves primitive and context selection; production test vectors, interop vectors, audits, and implementation profiles remain open. | Critical |
| DG-07 | `AR-22`, `AR-23`, `AR-24`, `AR-25`, `AR-26`, `AR-30` | Boomlet assurance is assumed, not demonstrated | The central trust anchor is expected to resist extraction, side channels, bias, cloning, and endurance failures, but there is no attestation, audit, or hardware assurance story in this repo. |  | Critical |
| DG-08 | `AR-31`, `AR-32`, `AR-33`, `AR-34`, `AR-35`, `AR-38`, `AR-39`, `AR-75` | The ST trust model is stronger than the current prototype evidence | The ST is treated like a single-purpose trusted appliance, while the referenced Portenta/Breakout materials emphasize prototyping, boot modes, debug, exposed signals, and flexible I/O. |  | Critical |
| DG-09 | `AR-38`, `AR-39`, `AR-75` | Prototype attack surface is not converted into a hardened ST build profile | The repo does not yet define which interfaces are removed, fused off, sealed, or monitored in the ST build, despite the prototype exposing multiple attack-friendly interfaces. |  | High |
| DG-10 | `AR-37`, `AR-40`, `AR-41`, `AR-42`, `AR-43`, `AR-46`, `AR-47`, `AR-71` | Endpoint transition and replacement procedures are missing | The design requires moving hardware between hosts and anticipates replacing Phone/Niso/ST, but those procedures are ancillary only and not yet defined. |  | High |
| DG-11 | `AR-44`, `AR-45`, `AR-59`, `AR-60`, `AR-61`, `AR-67` | Dynamic doxing data integrity is largely delegated to the phone and SAR operations | Rescue quality depends on phone-sourced data staying correct and current, but the repo explicitly admits little protection against phone compromise or feed stoppage. |  | High |
| DG-12 | `AR-55`, `AR-56`, `AR-57`, `AR-58`, `AR-62` | WT is a critical coordination dependency without a finalized failover or accountability model | WT is non-custodial but still central to liveness, freshness, routing, and metadata exposure, and the design defers switching/redundancy procedures to future ancillaries. |  | Critical |
| DG-13 | `AR-59`, `AR-60`, `AR-61`, `AR-62`, `AR-63` | SAR governance, abuse resistance, and jurisdiction handling remain operational assumptions | The repo depends on reputation, SAR operator choice, and jurisdictional fit, but does not yet specify controls against SAR misuse, compulsion, or ineffective response. |  | Critical |
| DG-14 | `AR-48`, `AR-49`, `AR-50`, `AR-51`, `AR-52`, `AR-53`, `AR-54`, `AR-71` | Peer governance is under-specified for blame, timeout, and non-cooperation | N-of-N is intentional, but the repo still lacks final procedures for peer delay, blame, expulsion, recovery from silence, or coordination breakdown. |  | High |
| DG-15 | `AR-14`, `AR-35`, `AR-36`, `AR-51`, `AR-74` | Human availability is not yet reconciled with random duress checks and freshness limits | The design wants unpredictable checks, but also recognizes users sleep, travel, live in different time zones, and can be delayed under ordinary conditions. |  | High |
| DG-16 | `AR-66`, `AR-67`, `AR-68`, `AR-69` | Privacy leakage is inventoried but not yet turned into a minimization strategy | The WIP leakage workbook shows large sensitive-data surface area, but the repo does not yet consolidate which disclosures are acceptable, avoidable, or must be redesigned. |  | High |
| DG-17 | `AR-18`, `AR-19`, `AR-20`, `AR-21`, `AR-60` | ~~Several safety properties are still context-derived rather than explicitly bound per message~~ Message binding is preserved as a resolved historical gap | ~~The WIP freshness and integrity artifacts show messages whose safety is recovered indirectly, by outer context or later checks, rather than by direct authoritative binding.~~ Current `SPEC.md` defines canonical envelope contexts, scope IDs, and directional channel keys. | Resolved in 96734855a35db6af7c6d8be06d72d452433bbc6b by canonical envelope contexts, scope IDs, and directional channel keys. | High |
| DG-18 | `AR-64`, `AR-65`, `AR-66`, `AR-69` | The network trust model is incomplete | Tor is assumed for privacy and availability, direct RPC is assumed safe enough, and signed onion addresses are assumed sufficient, but correlation, censorship, and routing edge cases are not fully modeled. |  | Medium |
| DG-19 | `AR-72`, `AR-73`, `AR-74` | The protocol is not yet backed by formal or simulation-based validation of timing behavior | The repo itself notes that complexity and dynamic behavior may produce unexpected delays and failures, but the validating simulations are still future work. |  | High |
| DG-20 | `AR-05`, `AR-71`, `AR-72` | Too many security-critical properties are still expressed as future ancillaries or operator discipline | The current design can explain how the happy path works, but many real-world safety properties still live outside the protocol core. |  | High |
| DG-21 | `AR-18`, `AR-19`, `AR-70`, `FM-14` | ~~Withdrawal-session binding is still implicit rather than protocol-canonical~~ Withdrawal-session binding is preserved as a resolved historical gap | ~~The design relies on approvals, commitments, pings, and signing readiness all belonging to one withdrawal attempt, but it does not yet define one authenticated session identifier or transcript bundle spanning the whole ceremony.~~ Current `SPEC.md` uses `withdrawal_id` and `approved_withdrawal_id`. | Resolved in 96734855a35db6af7c6d8be06d72d452433bbc6b by `withdrawal_id` and `approved_withdrawal_id`. | Critical |
| DG-22 | `AR-12`, `AR-16`, `AR-19`, `AR-50`, `FM-15` | ~~The transaction-authorization contract between early approval and final signing is under-specified~~ Transaction-authorization binding is preserved as a resolved historical gap | ~~The withdrawal docs require the hydrated PSBT to preserve the committed `tx_id`, but they do not yet specify the exact allowed mutations, satisfiability checks, authoritative hydrator behavior, independent operator-side verification duties, or rejection rules when hydration changes more than expected.~~ Current `SPEC.md` requires PSBT hydration constraints, reached-collection checks, signing-package verification, and final `tx_id` equality. | Resolved in 96734855a35db6af7c6d8be06d72d452433bbc6b by PSBT hydration constraints and signing-package verification. | High |
| DG-23 | `AR-18`, `AR-20`, `AR-60`, `FM-16`, `FM-23` | ~~SAR acknowledgement semantics are still under-specified at the protocol-document level~~ SAR acknowledgement binding is preserved as a resolved historical gap | ~~The model now binds acknowledgements to exact placeholder instances and replay memory, but the design docs still do not give one canonical transcript object or operational failure policy for SAR acknowledgement delivery.~~ Current `SPEC.md` defines exact placeholder acknowledgements, retry/failure behavior, and replay memory. | Resolved in 96734855a35db6af7c6d8be06d72d452433bbc6b by exact placeholder acknowledgements, retry/failure handling, and replay memory. | High |
| DG-24 | `AR-14`, `AR-55`, `AR-58`, `AR-60`, `AR-71`, `FM-17` | Honest-path liveness still depends on unstated fairness and timeout policy | The protocol narrative says withdrawal should complete when parties cooperate, but the docs still do not define the scheduler, retry, timeout, or service-progress assumptions precisely enough to support unqualified liveness claims. |  | High |
| DG-25 | `AR-14`, `AR-18`, `AR-57`, `FM-18` | Freshness evidence retention and auditability are not yet protocol-canonical | The security story depends on later steps still being grounded in the right accepted freshness evidence, but the design docs still do not define how such evidence is serialized, retained, or audited later when chain height keeps moving. |  | High |
| DG-26 | `AR-59`, `AR-60`, `AR-62`, `FM-19` | ~~The single-SAR-per-peer contract is not yet stated canonically in the design corpus~~ The single-SAR-per-peer contract is preserved as a resolved historical gap | ~~The formal model now treats SAR as exactly one SAR per peer, but the design corpus still needs to say that explicitly and remove residual ambiguous wording.~~ Current `SPEC.md` states one selected SAR identity per peer and setup-bound SAR routing. | Resolved in 96734855a35db6af7c6d8be06d72d452433bbc6b by ADR 0003 and setup-bound SAR routing. | High |
| DG-28 | `AR-09`, `AR-13`, `AR-71`, `FM-21` | Mid-ceremony interaction between boomerang progress and fallback opening is under-specified | The model can represent fallback availability before broadcast and fairness-backed fallback progress, but the design docs still do not define one canonical operator procedure for what honest peers should do when boomerang progress and deterministic fallback availability overlap. |  | High |
| DG-29 | `AR-18`, `AR-20`, `FM-22`, `FM-23` | ~~Placeholder-instance lifecycle is not yet protocol-canonical~~ Placeholder-instance lifecycle is preserved as a resolved historical gap | ~~The model now depends on unique opaque placeholder instances and replay memory, but the design docs still describe that mostly through narrative IV language rather than one canonical transcript/data structure.~~ Current `SPEC.md` binds placeholders to `approved_withdrawal_id`, requires fresh IVs, and records SAR replay tuples. | Resolved in 96734855a35db6af7c6d8be06d72d452433bbc6b by per-instance IVs, `approved_withdrawal_id` binding, and SAR replay tuples. | High |
| DG-30 | `AR-25`, `AR-71`, `FM-24` | Post-withdrawal cleanup and reset semantics are still only partly specified in the design corpus | The model now carries explicit reset and `mystery` regeneration after successful broadcast, but the design docs still need one canonical cross-component cleanup contract and failure policy if cleanup is interrupted. |  | High |
| DG-31 | `AR-18`, `AR-31`, `AR-33`, `FM-25` | ST/Boomlet transcript encoding is still under-specified below the nonce-bound transcript level | Current `SPEC.md` defines nonce-bound ST/Boomlet challenge-response contexts and the duress vocabulary; implementation-level serialized prompt/test-vector coverage remains incomplete. | Current `SPEC.md` partially resolves this; UI-level encoding, parser vectors, and human-factor validation remain open. | High |
| DG-32 | `AR-20`, `AR-55`, `AR-60`, `AR-66`, `FM-06`, `FM-26` | ~~End-to-end duress indistinguishability still lacks a timing and error-discipline contract~~ Duress indistinguishability service discipline is preserved as a resolved historical gap | ~~The design promises no observable message change and no duration change under duress, but the current formal model only checks a structural public-envelope surrogate and does not cover service latency, retries, timing equalization, or distinguishable operational side effects at WT/SAR.~~ Current `SPEC.md` defines identical WT-visible acknowledgement shape, retry, timing class, logging, metrics, and failure behavior for valid safe and duress placeholders. | Resolved in 96734855a35db6af7c6d8be06d72d452433bbc6b by timing, retry, logging, and externally observable failure rules. | Critical |
| DG-33 | `AR-17`, `AR-23`, `AR-74`, `FM-28` | Recurring-duress PRNG source and state are still not protocol-canonical | The withdrawal docs and diagrams are clear that repeated duress checks are triggered by a modulo test on a pseudo-random number, but they still do not say what is being sampled, whether the PRNG state is persistent, how draws are audited, or whether peers must have independent PRNG streams. The models therefore implement the modulo rule directly while leaving the generator semantics as an explicit proof-boundary abstraction. |  | High |
| DG-34 | `AR-76` | Software supply chain and service implementation security remain under-specified | The threat model already treats update/build compromise and WT/SAR service compromise as first-class risks, but the design corpus still lacks a final trust model for build provenance, update authorization, deployment hardening, patching discipline, and secure service operation. |  | High |

## Practical Reading Of The Register

The assumption register shows that Boomerang's current design is strongest where it narrows on-chain authorization semantics and weakest where it depends on:

- specialized trusted hardware without a complete assurance story;
- long-running coordination and timing parameters that are not yet fixed;
- external service providers that are non-custodial but still mission-critical;
- operational discipline standing in for protocol enforcement;
- future ancillary procedures to close realistic lifecycle events.

That does not make the design invalid. It does mean the current maturity is best described as:

- strong research direction;
- rich protocol specification;
- incomplete security closure.

## Recommended Next Use Of This Document

This register can now be used as the input to:

1. a formal trust-assumptions audit;
2. a design-roadmap prioritized by `DG-*` items;
3. a "must close before production" checklist;
4. a narrower threat model for prototype implementations of Boomlet and ST.
