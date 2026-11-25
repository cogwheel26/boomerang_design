# WT failover and Boomletwo recovery progress

The current recovery candidate uses self-contained ping checkpoints with an
offline designated Boomletwo for peers that chose backup. It has no continuous
ST or backup recording requirement; ordinary rotation and reset still apply.
Boomletwo activates through an independent ST duress check, exact SAR receipt
and a replacement certificate signed with its imported Boomlet key and its own
key. Recipients durably select the replacement identity for future actions.
An independent mystery draw needs a conservative floor; a checkpoint alone
does not establish latest state.

## Deliverables

| Deliverable | Files |
| --- | --- |
| WT failover rules | [Proposal](README.md), diagrams 01 through 08 |
| Independent activation and recipient identity update | [Lifecycle](../Cannon_boomletwo_lifecycle_proposal.md), [sequence](09_boomlet_rollover.puml) |
| Checkpoint and mystery policies | [Boomletwo candidate](boomlet_rollover.md), [sequence](09_boomlet_rollover.puml) |
| Candidate calculations and counterexamples | [Checks](boomlet_rollover_model.md) |
| WT wire draft | [Contract](wire_contract.md), [catalog](wire_catalog.json), [vectors](canonical_vectors.json) |
| Security requirements and limits | [Review](security_verification.md), [issues](security_issues.md), [requirements](security_requirements.md), [resources](resource_limits.md) |
| Separate WT and ordering experiments | [Existing model](security_model.md) |

## Evidence and limits

The checkpoint checks cover 1,152,921 conservative-threshold cases, including
stale counters. They reproduce immediate completion for 80 of 100 raw redraws
at counter 80. They also exhibit indistinguishable checkpoint observations
with different later duties, consent transitions and votes.

These checks count valid progress units; they do not prove elapsed block time,
latest-state recovery or implementation conformance of activation. Existing WT
models retain their separate scopes. The wire catalog does not yet allocate
checkpoint fields or a five-ping pong format.

## Required work

- [x] Select the two-key replacement certificate, independent activation duress
  check, exact SAR gate and durable recipient identity update.
- [ ] Define exact certificate and activation SAR encodings, dispatch, bounded
  storage and crash recovery; verify ST review and recipient installation.
- [ ] Preserve later or concealed rescue duties, consent transitions, WT votes
  and replay state without a continuously online ST or Boomletwo.
- [ ] Select the mystery policy and define recovery progress and incarnation
  rules, including already-reached state and fresh local signing sessions.
- [ ] Finish the bounded checkpoint schema, fixed padding, detached bundle,
  distribution and retention policy, and version-selected pong changes.
- [ ] Resolve authenticated chain observation and quantify fallback exposure
  from any additional recovery delay.
- [ ] Compose the complete mechanism with WT recovery, duress and signing;
  verify cryptographic encodings, device lifecycle and measured resource costs.
