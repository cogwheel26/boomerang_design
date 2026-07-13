# Boomerang Threat Model

> **Last change — 2026-07-13:** Split detailed architecture, attack trees, and threat scenarios into focused references; design-gap status and resolution evidence are unchanged.

Related material: [architecture](architecture.md), [attack trees](attack_trees.md),
and [threat mappings](audit_mappings.md). Appendix D remains the canonical
record of design-gap status and resolution evidence.

## Scope and assumptions

### System summary

Boomerang is a Bitcoin cold-storage protocol for cases where physical coercion
is a credible threat. A withdrawal is bounded in time, but the signing point is
not known in advance. Duress signaling runs through the ordinary withdrawal
flow.

The profile in `spec/SPEC.md` has exactly five peers and a 5-of-5 Boomerang
branch. A ceremony uses one WT; each peer selects one SAR, has one active
Boomlet, and may keep one inactive Boomletwo backup. A different peer count,
threshold, fallback tree, cryptographic profile, or checkpoint sequence is a
different protocol profile.

There are two spending paths. In the Boomerang path, spending starts after
`milestone_block_0` and only after every Boomlet reaches its private `mystery`
value through the freshness-checked ping/pong process. The fallback path uses
normal keys and a timelocked waterfall whose threshold eventually falls from
5-of-5 to 1-of-5.

Each on-chain `boom_pubkey_i` combines two keys with MuSig2: a mnemonic-backed
normal key used by Iso and a non-exportable share held by Boomlet. Compromising
the mnemonic is therefore not enough to sign through the Boomerang path.

ST presents the duress challenge and Boomlet evaluates the answer. Checks run
at commitment and at randomized points in the digging game. A safe placeholder
decrypts to zero padding; a duress placeholder decrypts to `doxing_key` or
equivalent unlock material. WT relays the placeholder to SAR, and SAR signs an
acknowledgement of the exact placeholder. This keeps the visible protocol flow
the same while giving Boomlet evidence of delivery.

Setup state is tied together by `setup_instance_id`, signed `PeerSetupRecord`
values, and chained `setup_checkpoint` values. Withdrawal approval uses
`withdrawal_id`; everything after unanimous approval uses
`approved_withdrawal_id`, including commitments, placeholders, pings, pongs,
reached-ping collections, signing, export, and replay state. WT may not advance
to commit and SAR processing until it has verified the non-initiators'
approval-set attestations.

### In-scope components

Peers are joint custodians of the bitcoin involved. Per peer or operator, with exactly five peers in the profile:

- **User:** the human operator.
- **Iso, offline:** key-derivation and signing environment for normal keys; interacts with Boomlet and ST.
- **Boomlet, secure element:** holds key share, enforces non-determinism, and runs duress logic.
- **Boomletwo, backup secure element:** authenticated target-bound import of Boomlet backup state *excluding* the active `mystery`; Boomletwo generates its own mystery after import, while activation procedure remains under design.
- **ST, Secure Terminal:** air-gapped, tamper-evident UI for user verification and duress challenges.
- **Niso, online:** networked coordinator per peer; handles Tor communications, talks to Bitcoin node RPC, interfaces with WT, and mediates QR flows to ST.
- **Phone:** used for SAR registration and the encrypted dynamic doxing feed.

External dependencies and services:

- **Bitcoin network / miners:** confirmation, timelocks, reorgs, fee market
- **Bitcoin node RPC endpoint(s)** used by each peer’s Niso
- **Tor network**
- **WT (Watchtower):** one active coordination service per ceremony, liveness oracle, and relay for signed PSBTs / transactions
- **SAR (Search & Rescue):** one selected SAR per peer; receives encrypted doxing data, detects duress, signs exact placeholder acknowledgements, and initiates physical response

### Out-of-scope

These security-relevant items are outside the model because the design leaves
them underspecified:

- SAR’s real-world response procedures
- Detailed organizational governance
- Manufacturing processes for Boomlet / ST hardware
- Wallet UX beyond what is specified by the protocol messages

### Primary assets

**Custody / value assets**
- **Bitcoin funds** locked by the Boomerang Taproot output
- **Transaction authorization correctness:** PSBT contents, destination, amounts, fees

**Key material & cryptographic assets**
- `mnemonic`, `passphrase`, and derived **normal private keys**
- Boomlet-held `boom_musig2_privkey_share`, non-exportable
- Boomlet identity keypair for signing and encryption
- ST identity keypair for the Boomlet↔ST secure channel
- Tor onion-service secret keys for peer Niso addresses
- WT and SAR long-term signing / encryption keys

**Duress & safety assets**
- `duress_consent_set`
- user-chosen `doxing_password`, derived `doxing_key`, and derived `doxing_data_identifier`
- **Static doxing data** and **dynamic doxing feed**

**Protocol state assets**
- Per-Boomlet `mystery` and `counter`
- `boomerang_params` and `boomerang_descriptor`
- `setup_instance_id`, `setup_checkpoint`, `withdrawal_id`, and `approved_withdrawal_id`
- Approval collections, approval-set attestations, commits, pings, pongs, reached-ping collections, and signing-session state
- SAR placeholder replay tuples: `{approved_withdrawal_id, boomlet_identity_pubkey, duress_placeholder.iv}`
- Protocol transcripts
- Milestone schedule, `milestone_block_collection`

### Security objectives

**Funds protection**
- Prevent unauthorized spending in both regimes.
- Prevent silent transaction tampering.
- Ensure recoverability in the normal regime under loss scenarios, while managing the associated risk.

**Coercion resistance**
- Under coercion, reduce attacker confidence in *time to cash-out*.
- Provide unavoidable, plausibly deniable duress signaling with minimal observable divergence.
- Preserve a reaction window for SAR response and deterrence.

**Privacy & safety**
- Minimize metadata that could enable targeting of key holders.
- Protect doxing data and duress signals from unauthorized disclosure.
- Resist correlation attacks that deanonymize peers, schedules, or duress events.

**Integrity & liveness**
- Prevent protocol-state desynchronization and replay.
- Ensure withdrawal completes when honest peers cooperate and dependencies are available.
- Ensure failures degrade safely, preferably fail-closed in the Boomerang regime.

### High-impact assumptions

The risk ratings assume:

- Boomlet's secure-element boundary holds;
- ST remains trustworthy;
- the cryptography used by the message and signing flows holds;
- build, update, and deployment paths for Iso, Niso, ST, Boomlet, WT, and SAR
  are trustworthy enough;
- at least one peer is honest;
- Bitcoin timelocks behave as expected;
- Niso and WT obtain a trustworthy enough `most_work_bitcoin_block_height` for
  milestone gates, freshness checks, and counter advancement;
- setup IDs, withdrawal IDs, checkpoints, freshness checks, and signed
  transcripts keep each setup and ceremony separate;
- `tx_id` continuity, approval-set attestations, PSBT checks, signing-package
  verification, and final transaction validation preserve the operator's
  intent;
- a SAR acknowledgement refers to the exact placeholder and does not reveal
  whether the safe or duress path was taken;
- only one of Boomlet and Boomletwo is active for a peer identity;
- WT and SAR remain available; and
- peers have a secure out-of-band channel.

### Key unknowns blocking production readiness

Production-readiness claims remain blocked by:

- Exact values and selection policy for the non-determinism and duress-check parameters
- Reorg-handling policy
- WT / SAR redundancy model
- Cryptographic implementation evidence: canonical-encoding conformance, CBC/CMAC/KDF test vectors, interoperable signature/envelope vectors, and side-channel-safe implementation profiles
- Boomletwo activation / recovery protocol
- Software supply chain and update mechanisms
- Monitoring, alerting, and incident-response workflows

### Open design boundaries

Present security claims are limited by the following boundaries. Some are fixed
in the protocol; others remain open.

| Boundary | Why it matters |
| --- | --- |
| **Chain view and reorg policy** | Milestone gating, freshness, and counter advancement depend on chain view, but reorg and divergent-node policy remain undefined. |
| **Setup / withdrawal binding** | Core binding is specified through `setup_instance_id`, chained setup checkpoints, `withdrawal_id`, and `approved_withdrawal_id`. |
| **Hydrated PSBT authorization contract** | Transaction authorization is specified through `tx_id` continuity, signing-package verification, descriptor and transaction checks, and final broadcast `tx_id` checks. |
| **Boomlet and Boomletwo activation semantics** | Backup export and import exist, but activation, deactivation, and the one-active-device invariant remain undefined. |
| **Duress-placeholder lifecycle** | The lifecycle is specified through fresh placeholder envelopes, `approved_withdrawal_id` context binding, SAR signatures over the exact encrypted placeholder, replay tuples, and externally indistinguishable protocol behavior. |
| **Operational transitions** | Device movement, replacement, and recovery for Phone, Niso, ST, WT selection, and SAR-set changes remain only partly specified. |
| **Honest-path liveness / fairness policy** | Completion depends on peer availability, timeout policy, blame handling, and scheduler or service fairness that the corpus leaves undefined. |
| **Parameter selection and timing policy** | Security depends on workable choices for milestones, mystery range, duress cadence, and freshness tolerances. |
| **Cryptographic profile and canonical transcript encoding** | The profile specifies AES-256-CBC with PKCS#7, AES-CMAC encrypt-then-MAC, SP 800-108 CMAC KDF context separation, canonical object bytes, and scope-specific contexts; implementation evidence is outside protocol design. |
| **Trusted-hardware assurance boundary** | Boomlet and ST are treated as trusted boundaries; hardware assurance remains outside protocol design. |
| **Software supply chain and service implementation security** | Build, update, deployment, and ordinary service-hardening controls remain outside protocol design. |
| **WT / SAR service governance and accountability** | WT and SAR behavior, WT failover, single-SAR replacement after setup, misuse resistance, and jurisdictional fit remain only partly specified. |
| **Privacy and network exposure policy** | Tor, RPC, WT, SAR, and doxing-data flows lack a final minimization policy for metadata leakage, correlation, and acceptable exposure. |

Boomlet and ST are treated as trusted devices. The cited prototype materials do not establish the trusted-device assurance assumed by this model.

## Architecture and trust boundaries

Detailed boundary table, flows, diagrams, data classification, parameters, and
binding rules: [architecture.md](architecture.md).

Three boundaries dominate the security argument:

- Boomlet and ST must hold for the main authorization and duress claims.
- WT and the Bitcoin RPC path must remain available and give a trustworthy
  enough chain view.
- Physical security and operator behavior remain part of the protocol's
  coercion boundary.

<a id="human-physical-risk"></a>
## Human and physical risk

Physical coercion is part of the threat model. Human operators, facilities,
travel patterns, and operating discipline are all part of the attack surface.

### Human/physical threat scenarios

| Scenario                                                            | Trust boundaries involved          | Primary assets at risk                   | What can go wrong                                                                                    | Candidate mitigations, design and operations                                                                                                 |
| ------------------------------------------------------------------- | ---------------------------------- | ---------------------------------------- | ---------------------------------------------------------------------------------------------------- | -------------------------------------------------------------------------------------------------------------------------------------------- |
| **Coercion or wrench attack** on one peer during withdrawal         | TB-PHYS-PEER, TB-ST, TB-BOOMLET    | Funds, user safety, duress secrecy       | Attacker forces approvals or continuation, tries to detect or bypass duress, or holds the victim until completion | Boomerang non-determinism; duress checks via ST; SAR response; safe-room procedures; operator drills; split-knowledge procedures |
| **Coercion on multiple peers, kidnapping, or round-up**             | TB-PHYS-PEER, TB-OOB               | Funds, user safety                       | Attacker captures multiple peers, or learns enough identity and schedule data to stage a simultaneous round-up | Geographic dispersion; time-zone dispersion; compartmentalized peer identity sharing; travel OPSEC; independent alerting paths |
| **Insider collusion** among peers                                   | TB-OOB, TB-PHYS-PEER               | Funds, governance integrity              | Colluding peers wait out waterfall timelocks; or coordinate coercion                                 | Legal agreements; choose milestones to make late-stage far future; monitoring and alerts |
| **Social engineering, including phishing and fake ceremonies**      | TB-OOB, TB-PHYS-PEER, TB-SAR       | Normal keys, peer set integrity, rescue readiness, privacy | Steals mnemonics; reroutes peer or WT Tor addresses; tricks the operator into fake SAR enrollment or ceremony steps | Multi-channel fingerprint checks; pinned keys; authenticated SAR directory; training; anti-phishing playbooks |
| **Credential theft, including mnemonic or passphrase compromise**   | TB-PHYS-PEER, TB-ISO               | Normal keys                              | Theft or coerced disclosure enables later deterministic theft once normal-key stages open            | Strong passphrases; split backups; secure storage; anti-phishing discipline |
| **Process non-compliance, such as missed rollover or skipped checks** | TB-PHYS-PEER, TB-OOB             | Funds, coercion resistance               | Users miss rollover windows or skip required checks, allowing the protocol to drift into weaker deterministic stages | Mandatory rollover schedule; automated reminders; rehearsals; documented exception handling and sign-off |
| **Operator error, including wrong milestones, outputs, or network** | TB-PHYS-PEER, TB-ISO, TB-ST        | Funds, liveness                          | Setup produces the wrong descriptor or milestones; withdrawal signs the wrong transaction or wrong network | Strict checklists; independent operator-side transaction review on dedicated hardware; testnet rehearsals; sanity checks and invariants in Iso |
| **Travel and commute risk, including surveillance or ambush**       | TB-PHYS-PEER                       | User safety, anonymity                   | Attacker identifies peer movements and targets vulnerable moments                                    | Vary routines; secure transport; avoid role disclosure; compartmentalize identities; personal-security procedures |
| **Site access failures, including unauthorized storage access**     | TB-PHYS-PEER                       | Devices, backups                         | Evil-maid installs implants or swaps devices; steals backups                                         | Access control, alarms, cameras; tamper seals; inventory |
| **Device theft or tampering of ST or Boomlet**                      | TB-PHYS-PEER, TB-BOOMLET, TB-ST    | Duress secrecy, protocol integrity, keys | Attacker tampers with trusted devices, learns consent-set material, or destroys Boomerang-state devices to force fallback | Certified secure element; tamper resistance; secure storage; spare devices; incident response |
| **Environmental disasters, including fire, flood, or EMP**          | TB-PHYS-PEER                       | Devices, backups                         | Damage or destruction forces fallback or makes recovery impossible                                   | Geo-redundant storage; fireproof safes; Faraday protection; disaster recovery drills |
| **Power interruption during signing or backup procedures**          | TB-PHYS-PEER, TB-BOOMLET, TB-ISO   | Signing state, liveness                  | Interrupted sessions cause partial state, nonce reuse, or lost progress                              | Atomic signing sessions; anti-rollback; UPS; recovery paths |
| **Jurisdictional or legal coercion of SAR or operators**            | TB-JURIS, TB-SAR                   | PII, user safety, service availability   | SAR forced to reveal data, delay action, or refuse service; operator compelled disclosure            | Minimize PII; legal counsel; documented policies; transparency reports |

### Duress mechanism assumptions

The duress mechanism relies on three assumptions:

- The attacker cannot observe the ST display and the user's selection behavior
  well enough to learn the consent set.
- ST does not leak consent-set material.
- Users can reproduce the consent set reliably under stress, fatigue, or coercion.

These assumptions are operationally fragile. Cameras, multiple attackers, and controlled environments directly weaken them. Shielding, private environments, and operator drills remain necessary.

Primary coercion campaign: [Tree 0](attack_trees.md#tree-0-primary-attacker-campaign-steal-funds-under-coercion-or-force-deterministic-fallback).

### Operational hardening checklist

**People**
- Run regular coercion, recovery, and rollover drills.
- Minimize who knows peer identities and custody roles.

**Facilities**
- Use secure, access-controlled environments for setup, backup, and withdrawal ceremonies.
- Maintain tamper-evident seals and inspection logs for ST, Boomlet, and Boomletwo.
- Keep Boomlet, Boomletwo, and mnemonic backups in geographically separated storage.

**Travel**
- Avoid predictable patterns and role disclosure.
- Use secure transport and avoid carrying all critical devices or backups together.

**Incident response**
- Predefine device-loss, coercion-suspected, and missed-rollover playbooks.
- Maintain a rehearsed rollover or fund-movement plan before deterministic stages.

---


## Threat catalog

Detailed `T-*` scenarios and STRIDE mappings:
[audit_mappings.md](audit_mappings.md). The `R-*` entries prioritize risk at the
design level.


<a id="risk-register"></a>
## Risk register

Risk fields follow NIST SP 800-30r1: threat event, vulnerability or
predisposing condition, likelihood, impact, and response. Each risk maps to
threat IDs and CCSS v9 controls.

### Scoring method

- **Likelihood (1–5):** Rare → Almost certain
- **Impact (1–5):** Negligible → Catastrophic
- **Risk score:** `Likelihood × Impact`
  - 1–5 Low, 6–10 Medium, 11–15 High, 16–25 Critical

Scores use the design corpus as it stood on April 11, 2026. Only controls and
assumptions present in that corpus affect the score; roadmap work does not.

`Status` indicates whether the present posture depends mainly on controls, assumptions, or unresolved design gaps.

### Risk register table

| Risk ID | Risk | Score | Status | Canonical DG links | Notes |
| --- | --- | --- | --- | --- | --- |
| R-01 | Boomlet secure element compromise: key extraction or logic tamper | 15 | Assumption | DG-06, DG-07 | Assumes JavaCard-class extraction resistance, non-exportable Boomlet key shares, and fallback timelocks. |
| R-02 | ST compromise: tampering, code injection, or key extraction enabling duress bypass or consent-set exfiltration | 12 | Assumption | DG-08, DG-09, DG-31 | Depends on trusted ST firmware, non-extractable ST keys, air-gapped QR exchange, and tamper evidence. |
| R-03 | Forced determinism from device loss, bricking, or deliberate stalling | 15 | Gap | DG-03, DG-04, DG-30 | Waterfall timelocks and backup import exist; rollover policy and Boomletwo activation remain critical. |
| R-04 | Malicious or compromised peer exploits later waterfall stages or governance gaps | 10 | Control | DG-03, DG-14, DG-15 | Early stages require 5-of-5; later recoverability stages need governance and rollover discipline. |
| R-05 | Watchtower compromise or malicious operation | 12 | Gap | DG-01, DG-12, DG-18, DG-34 | Active WT behavior remains central to freshness, routing, coordination, liveness, and metadata exposure. |
| R-06 | SAR compromise, coercion, or rescue-data misuse | 12 | Gap | DG-11, DG-13, DG-16 | SAR sees encrypted rescue data until duress; governance, jurisdiction, and abuse resistance remain operational boundaries. |
| R-07 | Password-based `doxing_key` brute-force after SAR database or ciphertext exposure | 9 | Accepted by ADR 0005 | DG-11, DG-16 | User-chosen `doxing_password` is accepted by ADR 0005; no protocol-layer entropy threshold is enforced. |
| R-08 | Niso compromise tampers PSBT presentation, hydration, or Tor coordination | 16 | Gap | DG-10, DG-22, DG-31 | ST and Boomlet check `tx_id` continuity, while Niso hardening and hydrated-PSBT verification remain important. |
| R-09 | False block-height or eclipse attacks manipulate freshness checks and counters | 12 | Gap | DG-01, DG-25 | Depends on chain-view trust, WT height, Niso RPC, and explicit reorg/freshness policy. |
| R-10 | Replay, spoofing, serialization, or desync of protocol messages | 12 | Control/Gaps | DG-05, DG-17, DG-21, DG-23, DG-24, DG-25, DG-29 | Core binding fields are specified; parser hardening, evidence retention, timeout, and fairness remain boundaries. |
| R-11 | QR-code channel attacks through malformed payloads, parser bugs, swapping, or camera trickery | 12 | Control | DG-10, DG-31, DG-34 | Air-gap, signatures, and nonces help; parser hardening and operational QR controls remain necessary. |
| R-12 | Duress and rescue-signal leakage under observation, side channels, or coercion | 12 | Assumption | DG-15, DG-23, DG-29, DG-32 | Assumes consent entry is not observed and protocol-visible safe/duress behavior remains indistinguishable. |
| R-13 | WT, SAR, peer availability, or fairness gaps block withdrawal or rescue acknowledgement | 12 | Gap | DG-12, DG-13, DG-14, DG-24 | Active flow depends on one WT, one SAR per peer, peer availability, and non-canonical retry/blame policy. |
| R-14 | Implementation bugs in cryptography, signing, or state binding | 15 | Assumption | DG-06, DG-17, DG-21, DG-22, DG-23, DG-29 | Cryptographic profile and binding are specified; implementation evidence and test vectors remain essential. |
| R-15 | Operator and ceremony errors cause loss or forced determinism | 16 | Control | DG-02, DG-03, DG-10, DG-14, DG-15, DG-30 | User verification, signed fingerprints, multiparty agreement, backup, runbooks, and monitoring carry major risk. |
| R-16 | Deanonymization and targeting through Tor correlation, metadata leakage, or routine exposure | 8 | Control | DG-16, DG-18 | Tor and encrypted PSBTs reduce exposure; metadata minimization and payment unlinkability remain open. |
| R-17 | Out-of-band peer exchange compromise causes key substitution or MITM | 15 | Control | DG-05, DG-14, DG-17 | ST verification, signed `boomerang_params`, and WT sorted pubkeys depend on authenticated OOB practice. |
| R-18 | Boomletwo backup misuse bypasses non-determinism or clones state | 12 | Gap | DG-04, DG-30 | Backup excludes `mystery`; activation, deactivation, and one-active-device semantics remain canonical gaps. |
| R-19 | Device substitution during setup or withdrawal | 8 | Control | DG-07, DG-08, DG-09, DG-10 | Identity binding and user verification exist; hardware provenance and tamper evidence remain important. |
| R-20 | Logging and monitoring data leaks from WT, SAR, or Niso | 12 | Assumption | DG-16, DG-18, DG-34 | Logging, retention, and monitoring controls depend mainly on operator practice and service hardening. |
| R-21 | False duress from user mistake triggers SAR escalation | 6 | Control | DG-13, DG-32 | Duress checks are designed to resist typos; SAR playbooks and false-positive handling remain operational. |
| R-22 | False negative duress: delivery, acknowledgement, or response fails | 15 | Gap | DG-13, DG-23, DG-24, DG-29, DG-32 | Boomlet verifies exact SAR acknowledgements; service reliability and response procedures remain safety-critical. |
| R-23 | WT service-fee payment metadata links peer identity to custody participation | 9 | Control | DG-12, DG-16, DG-18 | WT invoices and receipts create privacy pressure; payment unlinkability remains an operational control. |
| R-24 | Software or firmware supply-chain compromise or malicious updates | 10 | Assumption | DG-07, DG-08, DG-34 | Build provenance, release signing, update integrity, and dependency control are trusted at this stage. |
| R-25 | Digging-game state-machine edge cases allow acceleration or stalling | 12 | Gap | DG-01, DG-02, DG-24, DG-25, DG-33 | Tolerance checks and sequence rules exist; adversarial timing, reorg, and recurring-duress semantics need validation. |
| R-26 | SAR enrollment false coverage | 12 | Gap | DG-13, DG-23, DG-26 | Setup includes invoice, sync, WT finalization, and Boomlet checks; no canonical end-to-end coverage receipt exists. |

---

## Attacker paths

Attack-tree source: [attack_trees.md](attack_trees.md). Covered campaigns:

1. theft under coercion or forced deterministic fallback;
2. PSBT tampering and broken transaction-intent continuity;
3. deliberate entry into deterministic fallback;
4. suppression or failure of duress-triggered rescue;
5. peer deanonymization followed by targeted coercion; and
6. Boomlet or ST supply-chain compromise.


<a id="mitigations-roadmap"></a>
## Mitigations & roadmap

The roadmap groups implementation and operational work by time horizon.

### Mitigation roadmap

| Horizon | Workstream | DG / Risk links | Verification focus | Resolution |
| :--- | :--- | :--- | :--- | :--- |
| Now | Validate and implement the specified cryptographic profile, canonical serialization, and test vectors. | DG-06 / R-14,R-10,R-25 | Independent crypto review, interop vectors, and serialization fuzzing. | `SPEC.md` fixes primitive choices; implementation evidence and test vectors remain open. |
| Now | Preserve a simple ST trust boundary for `tx_id` continuity, duress checks, and independent spend verification. | DG-22,DG-31 / R-08,R-15 | UX review, adversarial `tx_id` tests, and operator verification tests. | Resolved in 96734855a35db6af7c6d8be06d72d452433bbc6b by withdrawal IDs, PSBT hydration constraints, and signing-package verification. |
| Now | Harden Niso as a dedicated appliance. | DG-10,DG-22,DG-34 / R-08,R-20,R-11 | Hardening benchmark, penetration test, and malware simulation. |  |
| Now | Define and rehearse incident response for coercion, device loss, WT/SAR outage, and approaching milestones. | DG-03,DG-12,DG-13,DG-15,DG-24 / R-15,R-03,R-22,R-13 | Tabletop exercises, runbook reviews, and drills. |  |
| Now | Formalize rollover policy, milestone monitoring, alerts, reminders, and dashboards. | DG-02,DG-03,DG-15 / R-15,R-03,R-04 | Operational audit, testnet rollover drill, and monitoring tests. |  |
| Next | Build multi-WT architecture with provider diversity, jurisdiction diversity, transparency logs, and HSM-backed WT keys. | DG-12,DG-16,DG-18,DG-34 / R-05,R-13,R-16 | Failover tests, WT security audit, and chaos testing. |  |
| Next | Design redundant SAR operations where policy permits, with audited access and uncertain-duress playbooks. | DG-13,DG-23,DG-24,DG-32 / R-06,R-22,R-21 | End-to-end duress drills, privacy audit, SLA testing, and false-positive exercises. |  |
| Next | Evaluate Boomlet and ST hardware security for side channels, fault injection, supply chain, and tamper evidence. | DG-07,DG-08,DG-09 / R-01,R-02,R-19 | Independent lab reports, teardown reviews, and provenance controls. |  |
| Next | Formalize Boomletwo activation and recovery while preserving the one-active-device invariant. | DG-04,DG-30 / R-18,R-03 | Design review, adversarial recovery tests, and formal invariants. |  |
| Later | Formally verify and simulate the digging-game state machine under adversarial delays, reorgs, and equivocation. | DG-01,DG-24,DG-25,DG-33 / R-25,R-09,R-10 | TLA+/Ivy model, simulation harness, and third-party review. |  |
| Later | Add advanced privacy protections for traffic shape, payment unlinkability, and anonymity-set management. | DG-16,DG-18 / R-16,R-23,R-20 | Traffic analysis tests, chain analysis, and privacy audit. |  |

### Component-specific hardening summary

**Boomlet**
- Secure-element selection and evaluation
- Anti-rollback counters
- Strict parsing
- Signed applets
- Minimal command surface
- Persist transcript commitments to prevent replay or equivocation acceptance

**ST**
- Secure boot
- Signed firmware
- No radios
- Hardened QR parser
- Anti-shoulder-surf UI
- Physical tamper evidence

**Iso**
- True air-gap
- Minimal OS
- Deterministic builds
- Controlled media only
- Deterministic key-derivation test vectors and fingerprint displays

**Niso**
- Hardened appliance
- Minimal services
- Strict network egress
- Disk encryption
- Log minimization
- Safe QR display and capture handling

**WT**
- Key protection and rotation
- Metadata minimization
- Rate limiting
- Onion-service hardening
- Privacy-preserving logging and retention limits
- Failover design and transparency logs as next-stage work

**SAR**
- PII minimization
- Retention limits
- Key protection and audited signing-key management
- Audited access
- Coverage-confirmation checks
- Redundant on-call coverage where policy permits

---

<a id="audit-mapping-summary"></a>
## Audit framework

- **STRIDE:** Spoofing and tampering center on identity binding, setup records, PSBT authorization, and WT-mediated collections.
- **Information disclosure:** Main exposure paths are SAR/WT metadata, Tor correlation, doxing-data handling, and Niso or phone logs.
- **Denial of service:** WT/SAR availability, peer non-cooperation, Tor availability, Bitcoin fee pressure, and Boomlet/ST failure drive liveness risk.
- **Elevation of privilege:** Secure-element compromise, ST firmware compromise, QR parser bugs, and host-driven state-machine abuse dominate escalation risk.
- **OWASP:** WT, SAR, the phone app, and networked Niso inherit ordinary application-security duties: secure design, input validation, access control, logging, DoS resistance, update integrity, and secure configuration.
- **CCSS:** Boomerang targets CCSS Level III expectations for key generation, key storage, backup, service-provider controls, operator environment, auditing, updates, incident response, and data retention.

---

<a id="appendix-design-gaps"></a>
## Appendix D: Detailed design gaps

### Protocol, timing, and transaction semantics

| Gap ID | Design gap | Why it matters | Priority | Status / Resolution |
| --- | --- | --- | --- | --- |
| DG-01 | No explicit reorg and block-oracle policy | The protocol depends on `most_work_bitcoin_block_height`, but the corpus leaves reorg handling, node trust boundaries, and divergent chain-view behavior undefined. | Critical | Open |
| DG-02 | No parameter-selection framework for milestones, mystery range, and freshness windows | The security story depends on suitable timing constants, but the design does not specify how to choose or validate them. | Critical | Open |
| DG-03 | Forced determinism is controlled mostly by user discipline and peer behavior | Late start, device loss, and non-cooperation are collapse paths, and the mitigation depends mainly on timely rollover and careful operation. | Critical | Open |
| DG-05 | Setup uniqueness and anti-replay | `setup_instance_id`, `peer_setup_nonce`, and chained setup checkpoints separate one setup from another. | High | Resolved in 96734855a35db6af7c6d8be06d72d452433bbc6b by `setup_instance_id`, `peer_setup_nonce`, and setup checkpoints. |
| DG-06 | Cryptographic implementation evidence is outside protocol design | `SPEC.md` fixes AES-256-CBC/PKCS#7, AES-CMAC encrypt-then-MAC, SP 800-108 CMAC KDF contexts, canonical bytes, and scope-specific binding. | Critical | Primitive and context selection are specified; implementation evidence remains separate. |
| DG-17 | Message binding | Canonical envelope contexts, scope IDs, and directional channel keys bind messages to their channel and purpose. | High | Resolved in 96734855a35db6af7c6d8be06d72d452433bbc6b by canonical envelope contexts, scope IDs, and directional channel keys. |
| DG-21 | Withdrawal-session binding | `withdrawal_id` and `approved_withdrawal_id` keep approvals, commitments, pings, signing readiness, and replay scope on the same withdrawal attempt. | Critical | Resolved in 96734855a35db6af7c6d8be06d72d452433bbc6b by `withdrawal_id` and `approved_withdrawal_id`. |
| DG-22 | Transaction-authorization binding | PSBT hydration constraints, reached-collection checks, signing-package verification, and final `tx_id` equality preserve the approved transaction. | High | Resolved in 96734855a35db6af7c6d8be06d72d452433bbc6b by PSBT hydration constraints and signing-package verification. |
| DG-23 | SAR acknowledgement binding | SAR acknowledges the exact placeholder, with defined retry and failure behavior and replay memory. | High | Resolved in 96734855a35db6af7c6d8be06d72d452433bbc6b by exact placeholder acknowledgements, retry/failure handling, and replay memory. |
| DG-24 | Honest-path liveness depends on unstated fairness and timeout policy | Withdrawal completion requires scheduler, retry, timeout, and service-progress assumptions that are not defined precisely enough to support unqualified liveness claims. | High | Open |
| DG-25 | Freshness evidence semantics are not protocol-canonical | Later steps depend on accepted freshness evidence remaining attributable to the correct ceremony state, but the design does not define how that fact carries forward as chain height changes. | High | Open |
| DG-28 | Mid-ceremony interaction between boomerang progress and fallback opening is under-specified | The design does not define one canonical operator procedure for overlap between boomerang progress and deterministic fallback availability. | High | Open |
| DG-29 | Placeholder-instance lifecycle | Every placeholder has a fresh IV, an `approved_withdrawal_id`, and a SAR replay tuple. | High | Resolved in 96734855a35db6af7c6d8be06d72d452433bbc6b by per-instance IVs, `approved_withdrawal_id` binding, and SAR replay tuples. |
| DG-30 | Post-withdrawal cleanup and reset semantics are partly specified | The design needs one canonical cross-component cleanup contract and failure policy if cleanup is interrupted after signing or broadcast. | High | Open |
| DG-31 | ST/Boomlet transcript semantics below the nonce-bound transcript are under-specified | `SPEC.md` defines nonce-bound ST/Boomlet challenge-response contexts and the duress vocabulary; the remaining protocol question is the exact semantic content that ST and Boomlet must agree on for each prompt. | High | Partly resolved by `SPEC.md`; implementation-level prompt rendering is outside protocol design. |
| DG-32 | End-to-end duress indistinguishability timing and error discipline | Valid safe and duress placeholders have the same WT-visible acknowledgement shape, retry policy, timing class, and failure behavior. | Critical | Resolved in 96734855a35db6af7c6d8be06d72d452433bbc6b by externally observable protocol behavior rules. |
| DG-33 | Recurring-duress random trigger semantics are not protocol-canonical | The repeated duress-check trigger rule is described, but the design does not specify the protocol-level source, state, and independence requirements for recurring-check draws. | High | Open |

### Boomlet, ST, and endpoint platform assurance

| Gap ID | Design gap | Why it matters | Priority | Status / Resolution |
| --- | --- | --- | --- | --- |
| DG-04 | Boomletwo activation and anti-clone semantics are unspecified | Backup existence is described, and `SPEC.md` defines authenticated backup import excluding active `mystery`, but the design does not define safe Boomlet deactivation and Boomletwo activation without duplicate authority. | Critical | Open |
| DG-07 | Boomlet assurance is assumed, not demonstrated | The central trust anchor is expected to resist extraction, side channels, bias, cloning, and endurance failures, but there is no attestation, audit, or hardware assurance story in this repo. | Critical | Open |
| DG-08 | The ST trust model is stronger than the current prototype evidence | The ST is treated like a single-purpose trusted appliance, while the referenced Portenta and breakout materials emphasize prototyping, boot modes, debug access, exposed signals, and flexible I/O. | Critical | Open |
| DG-09 | Prototype attack surface is not converted into a hardened ST build profile | The design does not define which interfaces are removed, fused off, sealed, or monitored in the ST build despite the prototype exposing multiple attack-friendly interfaces. | High | Open |
| DG-10 | Endpoint transition and replacement procedures are missing | The design requires moving hardware between hosts and anticipates replacing Phone, Niso, and ST, but those procedures are ancillary only and not defined. | High | Open |

### Services, operators, and recovery

| Gap ID | Design gap | Why it matters | Priority | Status / Resolution |
| --- | --- | --- | --- | --- |
| DG-34 | Software supply chain and service implementation security remain under-specified | Update/build compromise and WT/SAR service compromise are first-class risks, and the design lacks a final trust model for build provenance, update authorization, deployment hardening, patching discipline, and secure service operation. | High | Open |
| DG-11 | Dynamic doxing data integrity and confidentiality are largely delegated to the phone, user password choice, and SAR operations | Rescue quality depends on phone-sourced data staying correct and current; rescue-data confidentiality after ciphertext exposure depends on the user-chosen `doxing_password`; the design gives little direct protection against phone compromise or feed stoppage. | High | Open |
| DG-12 | WT is a critical coordination dependency without a finalized failover or accountability model | WT is non-custodial but central to liveness, freshness, routing, and metadata exposure, and switching or redundancy procedures remain deferred. | Critical | Open |
| DG-13 | SAR governance, abuse resistance, and jurisdiction handling remain operational assumptions | The design depends on reputation, SAR operator choice, and jurisdictional fit, but does not specify controls against SAR misuse, compulsion, or ineffective response. | Critical | Open |
| DG-14 | Peer governance is under-specified for blame, timeout, and non-cooperation | N-of-N is intentional, but the design lacks final procedures for peer delay, blame, expulsion, recovery from silence, or coordination breakdown. | High | Open |
| DG-15 | Human availability is not reconciled with random duress checks and freshness limits | The design wants unpredictable checks, but users sleep, travel, live in different time zones, and can be delayed under ordinary conditions. | High | Open |
| DG-19 | The protocol lacks formal or simulation-based validation of timing behavior | The design notes that complexity and dynamic behavior may produce unexpected delays and failures, but the validating simulations remain future work. | High | Open |
| DG-20 | Security-critical properties depend on future ancillaries or operator discipline | The design explains the cooperative path, but many real-world safety properties live outside the protocol core. | High | Open |
| DG-26 | Single-SAR-per-peer contract | Each peer selects one SAR identity, and SAR routing is bound during setup. | High | Resolved in 96734855a35db6af7c6d8be06d72d452433bbc6b by ADR 0003 and setup-bound SAR routing. |

### Privacy and network exposure

| Gap ID | Design gap | Why it matters | Priority | Status / Resolution |
| --- | --- | --- | --- | --- |
| DG-16 | Privacy leakage is inventoried but not turned into a minimization strategy | The leakage analysis shows a large sensitive-data surface area, including password-bounded SAR ciphertext exposure, but the design does not consolidate which disclosures are acceptable, avoidable, or must be redesigned. | High | Open |
| DG-18 | The network trust model is incomplete | Tor is assumed for privacy and availability, direct RPC is assumed safe enough, and signed onion addresses are assumed sufficient, but correlation, censorship, and routing edge cases are not fully modeled. | Medium | Open |
