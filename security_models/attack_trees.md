# Boomerang attack trees

> **Last change — 2026-07-13:** Moved the attack trees out of the main threat model without changing their controls, assumptions, or open dependencies.

### Tree 0: Primary attacker campaign: steal funds under coercion or force deterministic fallback

Green nodes are controls; yellow nodes are assumptions or open dependencies.

```mermaid
flowchart TD
  A["Goal: Steal funds under coercion or by forcing deterministic fallback"] --> OR0{OR}
  OR0 --> B["Force spend in Boomerang regime"]
  OR0 --> C["Force spend in normal regime at an attainable threshold"]

  B --> AND1((AND))
  AND1 --> B0["Reach milestone_block_0 (or wait until it is reached)"]
  AND1 --> B1["Control all N required peers"]
  AND1 --> B2["Obtain all required signing material and ceremony/device access"]
  AND1 --> B3["Sustain coercive control until all mystery thresholds are reached"]

  B1 --> AND2((AND))
  AND2 --> B1a["Deanonymize and locate peer set"]
  AND2 --> B1b["Physically capture or control each required peer"]
  AND2 --> B1c["Prevent refusal, escape, or loss of control over any one peer"]

  B2 --> AND3((AND))
  AND3 --> B2a["Force access to Boomlet, ST, and operator workflow"]
  AND3 --> B2b["Force disclosure or use of mnemonic and passphrase for each required peer"]
  AND3 --> B2c["Compel repeated approvals and participation through the ceremony"]

  B3 --> AND4((AND))
  AND4 --> B3a["Sustain detention and logistics through bounded but unpredictable delay"]
  AND4 --> B3b["Prevent abort from timeout, ops failure, or peer loss"]

  %% ----------------------------
  %% Normal-regime coercion path
  %% ----------------------------
  C --> AND5((AND))
  AND5 --> C1["Control K normal keys at spend time"]
  AND5 --> C2["Reach a milestone where normal-regime threshold ≤ K"]
  AND5 --> C3["Ensure defenders do not successfully exit earlier while threshold > K"]

  C1 --> AND6((AND))
  AND6 --> C1a["Coerce K normal-key holders or mnemonic custodians"]
  AND6 --> C1b["Retain extracted key material until spend"]

  C3 --> OR1{OR}
  OR1 --> C3a["Begin coercion only after the threshold has already degraded to K"]
  OR1 --> C3b["Start earlier and block earlier defender exit paths until threshold degrades"]

  C3b --> AND7((AND))
  AND7 --> C3b1["Prevent timely rollover before the milestone"]
  AND7 --> C3b2["Prevent earlier normal-regime withdrawal while threshold > K"]
  AND7 --> C3b3["If needed, prevent Boomerang-regime completion"]

  C3b3 --> OR2{OR}
  OR2 --> C3b3a["Destroy or steal Boomlet and prevent backup use"]
  OR2 --> C3b3b["Induce or exploit peer non-cooperation"]
  OR2 --> C3b3c["Rely on prior operational failure or late withdrawal start"]

  %% ----------------------------
  %% Controls and open items
  %% ----------------------------
  D1["Control: peer anonymity and OPSEC"] -.-> B1a
  D2["Control: geographic and temporal dispersion"] -.-> B1b
  D3["Control: N-of-N Boomerang regime"] -.-> B1
  D4["Control: device separation and ceremony checks"] -.-> B2a
  D5["Control: strong secrecy and custody of mnemonics and passphrases"] -.-> B2b
  D6["Control: bounded but unpredictable mystery thresholds"] -.-> B3a
  D7["Control: recurring duress checks and SAR response"] -.-> B3
  D8["Control: strong normal-key custody"] -.-> C1
  D9["Control: rollover before milestones"] -.-> C3b1
  D10["Boundary: backup export exists, but activation and recovery remain unresolved"] -.-> C3b3a

  classDef goal fill:#ffffff,stroke:#222,stroke-width:2px,color:#000;
  classDef attack fill:#ffcccc,stroke:#cc0000,color:#000;
  classDef control fill:#ccffcc,stroke:#009900,color:#000;
  classDef open fill:#fff2cc,stroke:#b38f00,color:#000;
  classDef gate fill:#ffffff,stroke:#333,stroke-width:2px,color:#000;

  class A goal;
  class B,C,B0,B1,B2,B3,B1a,B1b,B1c,B2a,B2b,B2c,B3a,B3b,C1,C2,C3,C1a,C1b,C3a,C3b,C3b1,C3b2,C3b3,C3b3a,C3b3b,C3b3c attack;
  class D1,D2,D3,D4,D5,D6,D7,D8,D9 control;
  class D10 open;
  class OR0,OR1,OR2,AND1,AND2,AND3,AND4,AND5,AND6,AND7 gate;

```

### Tree 1: Steal funds by tampering PSBT or breaking intent continuity

```mermaid
flowchart TD
  A["Goal: Steal funds by tampering the transaction or breaking intent continuity"] --> OR0{OR}

  OR0 --> B["Get a malicious PSBT approved by all required peers"]
  OR0 --> C["Cause a different PSBT or transaction to be signed than the one approved"]
  OR0 --> D["Exploit signing, parser, or state-machine implementation bugs"]

  %% ----------------------------
  %% 1) Malicious PSBT gets approved
  %% ----------------------------
  B --> AND1((AND))
  AND1 --> B1["Modify or substitute the PSBT before peer approval"]
  AND1 --> B2["Defeat or mislead operator verification at every required peer"]
  AND1 --> B3["Keep the malicious PSBT and tx_id presentation consistent across all approval synchronization steps"]

  B1 --> OR1{OR}
  OR1 --> B1a["Malware alters outputs, change, or fees before first verification"]
  OR1 --> B1b["Swap the PSBT or per-peer encrypted PSBT payload before recipient peer decrypts it"]

  B2 --> OR2{OR}
  OR2 --> B2a["Compromise initiator watch-only wallet or Niso view so the malicious PSBT appears intended"]
  OR2 --> B2b["Compromise non-initiator Niso verification views so the same malicious PSBT is accepted"]
  OR2 --> B2c["Exploit operator-review weakness so tx_id approval is given for a malicious but consistently presented PSBT"]

  %% ----------------------------
  %% 2) Intent continuity breaks after approval
  %% ----------------------------
  C --> AND2((AND))
  AND2 --> C1["Defeat tx_id and continuity protections across the withdrawal state machine"]
  AND2 --> C2["Make the final signed PSBT or transaction differ from the operator-approved one"]

  C1 --> OR3{OR}
  OR3 --> C1a["Exploit inconsistent PSBT parsing, tx_id derivation, or serialization across components"]
  OR3 --> C1b["Exploit replay or state-confusion bug despite nonce, freshness, and sequence checks"]
  OR3 --> C1c["Exploit approval-to-commit, commit-to-ping, or reached-state binding flaw"]

  C2 --> OR4{OR}
  OR4 --> C2a["Exploit PSBT hydration mismatch at finalization"]
  OR4 --> C2b["Exploit message substitution between reached-state verification and Iso/Boomlet signing"]

  %% ----------------------------
  %% 3) Direct implementation failures
  %% ----------------------------
  D --> OR5{OR}
  OR5 --> D1["PSBT parser or serializer bug causes signing of a different transaction"]
  OR5 --> D2["MuSig2 implementation bug: nonce, session, or transcript binding failure"]
  OR5 --> D3["State-machine bug skips or misapplies prerequisite approval or reached-state checks"]

  %% ----------------------------
  %% Controls and open items
  %% ----------------------------
  F1["Control: independent PSBT verification on operator tooling and ST tx_id approval at each peer"] -.-> B2
  F2["Control: repeated tx_id and freshness checks across approval, commitment, ping, pong, and reached-state"] -.-> C1
  F3["Control: nonces, recency, and sequence-number checks to block replay and stale-state reuse"] -.-> C1b
  F4["Control: duplicate validation in Niso and Boomlet, including final re-verification before signing"] -.-> C2
  F5["Assumption: correct PSBT and MuSig2 implementation on isolated Iso"] -.-> D1
  F6["Boundary: canonical session and transcript binding across the full ceremony"] -.-> D2
  F7["Boundary: complete state-machine hardening and prerequisite enforcement"] -.-> D3

  %% Styles
  classDef goal fill:#ffffff,stroke:#222,stroke-width:2px,color:#000;
  classDef attack fill:#ffcccc,stroke:#cc0000,color:#000;
  classDef control fill:#ccffcc,stroke:#009900,color:#000;
  classDef open fill:#fff2cc,stroke:#b38f00,color:#000;
  classDef gate fill:#ffffff,stroke:#333,stroke-width:2px,color:#000;

  class A goal;
  class B,C,D,B1,B2,B3,B1a,B1b,B2a,B2b,B2c,C1,C2,C1a,C1b,C1c,C2a,C2b,D1,D2,D3 attack;
  class F1,F2,F3,F4 control;
  class F5,F6,F7 open;
  class OR0,OR1,OR2,OR3,OR4,OR5,AND1,AND2 gate;

```


### Tree 2: Reach deterministic fallback and then steal with normal keys

```mermaid
flowchart TD
  A["Goal: Steal funds via the deterministic fallback regime"] --> AND0((AND))

  AND0 --> B["Control K normal keys at spend time"]
  AND0 --> C["Reach a milestone where the active normal-regime threshold ≤ K"]
  AND0 --> D["Ensure defenders do not successfully exit earlier while threshold > K"]

  %% ----------------------------
  %% 1) Obtain enough normal keys
  %% ----------------------------
  B --> OR1{OR}
  OR1 --> B1["Phish or steal mnemonic and passphrase backups"]
  OR1 --> B2["Compel disclosure under coercion"]
  OR1 --> B3["Insider or compromised peer retains their own normal key and waits"]

  %% ----------------------------
  %% 2) Prevent earlier defender exit
  %% ----------------------------
  D --> OR2{OR}
  OR2 --> D1["Begin the attack only after the threshold has already degraded to K"]
  OR2 --> D2["Start earlier and block earlier defender exit until the threshold degrades"]

  D2 --> AND1((AND))
  AND1 --> D2a["Prevent timely rollover before the degrading milestone"]
  AND1 --> D2b["Prevent earlier normal-regime withdrawal while threshold > K"]
  AND1 --> D2c["If needed, prevent Boomerang-regime completion"]

  D2c --> OR3{OR}
  OR3 --> D2c1["Destroy or steal Boomlet and prevent backup use"]
  OR3 --> D2c2["Induce or exploit peer non-cooperation"]
  OR3 --> D2c3["Exploit coordination failure or dependency outage to delay the ceremony"]
  OR3 --> D2c4["Exploit Boomlet or backup bug to brick or erase required state"]
  OR3 --> D2c5["Exploit prior operational failure or late withdrawal start"]

  %% ----------------------------
  %% Controls and open items
  %% ----------------------------
  E1["Control: strong mnemonic and passphrase custody, including split backups and secure storage"] -.-> B1
  E2["Control: coercion-resistant operating model, peer anonymity, and dispersion"] -.-> B2
  E3["Control: insider-risk controls and key-holder governance"] -.-> B3
  E4["Control: rollover before deterministic milestones"] -.-> D2a
  E5["Boundary: threshold schedule must keep low-threshold stages remote"] -.-> C
  E6["Control: secure storage and tamper-evident custody for Boomlet and Boomletwo"] -.-> D2c1
  E7["Boundary: backup activation and recovery semantics remain unresolved"] -.-> D2c1
  E8["Boundary: WT redundancy and failover remain unresolved"] -.-> D2c3

  %% Styles
  classDef goal fill:#ffffff,stroke:#222,stroke-width:2px,color:#000;
  classDef attack fill:#ffcccc,stroke:#cc0000,color:#000;
  classDef control fill:#ccffcc,stroke:#009900,color:#000;
  classDef open fill:#fff2cc,stroke:#b38f00,color:#000;
  classDef gate fill:#ffffff,stroke:#333,stroke-width:2px,color:#000;

  class A goal;
  class B,C,D,B1,B2,B3,D1,D2,D2a,D2b,D2c,D2c1,D2c2,D2c3,D2c4,D2c5 attack;
  class E1,E2,E3,E4,E6 control;
  class E5,E7,E8 open;
  class AND0,AND1,OR1,OR2,OR3 gate;

```

### Tree 3: Complete a coerced withdrawal without effective duress-triggered rescue

```mermaid
flowchart TD
  A["Goal: Complete a coerced withdrawal without effective duress-triggered rescue"] --> OR0{OR}

  OR0 --> B["Cause duress checks to evaluate as safe"]
  OR0 --> C["Prevent a true duress signal from producing actionable SAR response"]
  OR0 --> D["Infer hidden duress and react before rescue can disrupt the attack"]

  %% ----------------------------
  %% 1) Make duress appear safe
  %% ----------------------------
  B --> OR1{OR}
  OR1 --> B1["Observe the consent pattern or duress responses in a non-private environment"]
  OR1 --> B2["Compromise ST or the setup and relay path to learn or alter duress input"]
  OR1 --> B3["Compromise Boomlet so it reveals the consent pattern or mis-evaluates duress"]

  %% ----------------------------
  %% 2) True duress is generated, but SAR response is neutralized
  %% ----------------------------
  C --> OR2{OR}
  OR2 --> C1["Compromise SAR infrastructure or operators"]
  OR2 --> C2["Sabotage prior SAR registration so activation is not actionable"]
  OR2 --> C3["Tamper with or stop dynamic doxing data so rescue becomes less reliable"]

  %% ----------------------------
  %% 3) Duress stays hidden in protocol flow, but attacker infers it anyway
  %% ----------------------------
  D --> AND1((AND))
  AND1 --> D1["Infer hidden duress from side channels despite intended unchanged protocol flow"]
  AND1 --> D2["React before rescue meaningfully disrupts the withdrawal"]

  D2 --> OR3{OR}
  OR3 --> D2a["Escalate coercion or violence to suppress further signaling"]
  OR3 --> D2b["Accelerate the withdrawal before intervention lands"]
  OR3 --> D2c["Relocate or isolate the victim before intervention lands"]

  %% ----------------------------
  %% Controls and open items
  %% ----------------------------
  E1["Control: shielding, private environment, and user training"] -.-> B1
  E2["Control: tamper-evident ST and hardened setup and relay path"] -.-> B2
  E3["Assumption: Boomlet resists extraction and duress-state compromise"] -.-> B3
  E4["Boundary: authenticated SAR enrollment and operator accountability"] -.-> C1
  E5["Boundary: reliable SAR registration and coverage confirmation"] -.-> C2
  E6["Boundary: reliable Phone-to-SAR dynamic feed and ancillary recovery procedures"] -.-> C3
  E7["Boundary: protocol flow must remain observably constant on duress"] -.-> D1

  %% Styles
  classDef goal fill:#ffffff,stroke:#222,stroke-width:2px,color:#000;
  classDef attack fill:#ffcccc,stroke:#cc0000,color:#000;
  classDef control fill:#ccffcc,stroke:#009900,color:#000;
  classDef open fill:#fff2cc,stroke:#b38f00,color:#000;
  classDef gate fill:#ffffff,stroke:#333,stroke-width:2px,color:#000;

  class A goal;
  class B,C,D,B1,B2,B3,C1,C2,C3,D1,D2,D2a,D2b,D2c attack;
  class E1,E2 control;
  class E3,E4,E5,E6,E7 open;
  class OR0,OR1,OR2,OR3,AND1 gate;

```

### Tree 4: Deanonymize peers and target them with coercion

```mermaid
flowchart TD
  A["Goal: Identify at least one peer operator to target physically"] --> OR0{OR}

  OR0 --> B["Exploit network and communication metadata"]
  OR0 --> C["Exploit WT metadata or service-provider records"]
  OR0 --> D["Exploit SAR registration, payment, or account records"]
  OR0 --> E["Exploit out-of-band peer-data exchange or operator OPSEC failure"]
  OR0 --> F["Exploit insider leakage"]

  %% ----------------------------
  %% Network / communication deanonymization
  %% ----------------------------
  B --> OR1{OR}
  OR1 --> B1["Tor traffic or endpoint correlation against peer-to-peer or peer-to-WT communications"]
  OR1 --> B2["Compromise Niso, host, or local network environment to reveal peer communication metadata"]

  %% ----------------------------
  %% WT-side exposure
  %% ----------------------------
  C --> OR2{OR}
  OR2 --> C1["WT logs or retained metadata leak, subpoena, or compromise"]
  OR2 --> C2["WT registration or coordination records reveal peer IDs, params, or communication relationships"]

  %% ----------------------------
  %% SAR-side exposure
  %% ----------------------------
  D --> OR3{OR}
  OR3 --> D1["SAR payment invoice, receipt, or customer records leak, subpoena, or compromise"]
  OR3 --> D2["SAR registration or account metadata leak, subpoena, or compromise"]
  OR3 --> D3["SAR learns identity on duress, then turns rogue or later leaks that knowledge"]

  %% ----------------------------
  %% Out-of-band exchange / OPSEC failure
  %% ----------------------------
  E --> OR4{OR}
  OR4 --> E1["Intercept or compromise out-of-band sharing of peer IDs and signed Tor addresses"]
  OR4 --> E2["Operator reuses identifiable channels, accounts, or devices during peer coordination"]
  OR4 --> E3["Compromise a peer device that stores peer address collections or signed peer data"]

  %% ----------------------------
  %% Insider leakage
  %% ----------------------------
  F --> OR5{OR}
  OR5 --> F1["Malicious peer reveals peer contacts or identities"]
  OR5 --> F2["WT insider sells or discloses metadata"]
  OR5 --> F3["SAR insider sells or discloses registration or rescue data"]

  %% ----------------------------
  %% Controls and open items
  %% ----------------------------
  G1["Control: Tor hygiene, endpoint hardening, and communication-metadata minimization"] -.-> B
  G2["Boundary: WT log minimization, retention limits, and encryption"] -.-> C1
  G3["Boundary: minimize WT-visible metadata and compartmentalize identifiers"] -.-> C2
  G4["Boundary: privacy-preserving SAR payment and record minimization"] -.-> D1
  G5["Boundary: minimize SAR-held account metadata and compartmentalize identifiers"] -.-> D2
  G6["Control: secure out-of-band exchange discipline and operator OPSEC"] -.-> E
  G7["Control: compartmentalize peer knowledge and governance"] -.-> F1

  %% Styles
  classDef goal fill:#ffffff,stroke:#222,stroke-width:2px,color:#000;
  classDef attack fill:#ffcccc,stroke:#cc0000,color:#000;
  classDef control fill:#ccffcc,stroke:#009900,color:#000;
  classDef open fill:#fff2cc,stroke:#b38f00,color:#000;
  classDef gate fill:#ffffff,stroke:#333,stroke-width:2px,color:#000;

  class A goal;
  class B,C,D,E,F,B1,B2,C1,C2,D1,D2,D3,E1,E2,E3,F1,F2,F3 attack;
  class G1,G6,G7 control;
  class G2,G3,G4,G5 open;
  class OR0,OR1,OR2,OR3,OR4,OR5 gate;

```

### Tree 5: Supply-chain compromise of Boomlet and ST

```mermaid
flowchart TD
  A["Goal: Implant a backdoor into signing or duress hardware or its provisioning path"] --> OR0{OR}

  OR0 --> B["Compromise Boomlet or Boomletwo supply chain"]
  OR0 --> C["Compromise ST supply chain"]
  OR0 --> D["Compromise provisioning artifacts or installation environment"]

  %% ----------------------------
  %% Boomlet / Boomletwo compromise
  %% ----------------------------
  B --> OR1{OR}
  OR1 --> B1["Malicious or substituted secure-element or JavaCard platform"]
  OR1 --> B2["Malicious Boomlet applet installed before or during setup"]
  OR1 --> B3["Malicious Boomletwo backup applet installed before or during setup"]

  %% ----------------------------
  %% ST compromise
  %% ----------------------------
  C --> OR2{OR}
  OR2 --> C1["Backdoored ST firmware or software"]
  OR2 --> C2["Malicious ST hardware with hidden capture or exfiltration capability"]

  %% ----------------------------
  %% Provisioning / installation compromise
  %% ----------------------------
  D --> OR3{OR}
  OR3 --> D1["Compromise build artifacts so Iso installs malicious Boomlet, Boomletwo, or ST code"]
  OR3 --> D2["Compromise Iso or the provisioning workstation during installation"]

  %% ----------------------------
  %% Controls and open items
  %% ----------------------------
  E1["Boundary: vetted sourcing and hardware evaluation for secure elements"] -.-> B1
  E2["Control: applet verification and controlled provisioning"] -.-> B2
  E3["Boundary: Boomletwo backup provisioning assurance remains incomplete"] -.-> B3
  E4["Control: tamper-evident ST design and independent inspection"] -.-> C
  E5["Boundary: reproducible artifacts, review, and provenance checks"] -.-> D1
  E6["Control: trusted isolated Iso environment"] -.-> D2

  %% Styles
  classDef goal fill:#ffffff,stroke:#222,stroke-width:2px,color:#000;
  classDef attack fill:#ffcccc,stroke:#cc0000,color:#000;
  classDef control fill:#ccffcc,stroke:#009900,color:#000;
  classDef open fill:#fff2cc,stroke:#b38f00,color:#000;
  classDef gate fill:#ffffff,stroke:#333,stroke-width:2px,color:#000;

  class A goal;
  class B,C,D,B1,B2,B3,C1,C2,D1,D2 attack;
  class E2,E4,E6 control;
  class E1,E3,E5 open;
  class OR0,OR1,OR2,OR3 gate;

```
