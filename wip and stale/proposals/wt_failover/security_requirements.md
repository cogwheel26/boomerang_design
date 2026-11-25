# Proposed security-model integration

These controls and assumptions accompany the WT failover and designated Boomletwo
activation proposals. Adoption must incorporate them into the architecture,
assumption register, threat model, operational controls and conformance plan.
The base security-model documents remain separate from these proposals.

AR-82 through AR-89, R-29 through R-32 and T-FAILOVER-01 through
T-FAILOVER-08 are proposed integration identifiers.
R-29 covers lost rescue obligations or recovery artifacts; R-30 covers conflicting
authority or decisions; R-31 covers stale WT authority and replay; R-32 covers
resource exhaustion. Other identifiers refer to the base security model.

## Architecture


[WT_FAILOVER_V1](README.md) is a fresh profile over the base SPEC. One certified
head grants WT authority; candidate transport does not. Each Boomlet locally
checks its frozen state, SAR duty, votes, head and phase. Activation needs five
COMMIT votes, while ABORT preserves completed SAR discharges.

The originating Boomlet retains its fragment until permanent setup retirement.
External storage receipts authorize no cleanup. Profile limits bound load but can
reduce availability, and repeated switches expose service and timing metadata.

### Self-contained ping recovery

The [Boomletwo candidate](boomlet_rollover.md) keeps the designated backup
offline. After source loss, Boomletwo independently checks duress through ST,
obtains its exact activation SAR receipt and issues the two-key replacement
certificate defined in the lifecycle proposal. Recipients durably select its
identity for future actions. Its checkpoint proves state at one ping; current
state requires additional evidence. Recovery cannot lower the remaining progress
floor, replay historical pongs or bypass inherited protocol gates.

### Chain observation and recovery limits

The honest witness must remain the same logical peer throughout the history,
including the source and its designated backup after valid activation. Agreement between
compromised Niso and WT observations cannot establish real block progress.
AR-10, AR-11, AR-43 and AR-57 require an explicit authenticated-observation
mechanism before the delay guarantee can be established under that adversary.
The [verification report](security_verification.md) retains its counterexample.

Different first locks at two honest peers can prevent either switch combination
from collecting five reports. Completion assumes agreement before locking;
later cooperation alone may still require fallback. Locks cannot be discarded
to regain availability.

## Assumptions


These assumptions apply to [WT_FAILOVER_V1](README.md), which
requires a fresh setup and a separate complete wire version.

| ID | Assumption | Sources | If False | Status |
| --- | --- | --- | --- | --- |
| AR-82 | At least one honest logical peer preserves non-rollbackable protocol journals across identity replacement. Recipients durably retain its accepted identity and certificate. A designated backup completes the activation duress and SAR gates before certificate output. | WT proposal 3.3, 6; lifecycle | Regressed identities or missing voting history permit conflicting decisions. | Specified activation rules; device evidence pending |
| AR-83 | Each honest signer retains exact frozen placeholder bytes and verifies its own acknowledgment before initial activation PREPARE, and completes any required cleanup gates under SPEC Section 16.7. | WT proposal 5.2, 7.3 | Closure or candidate loss can discard rescue delivery. | Specified; bounded lifecycle checks |
| AR-84 | All five peers cooperate, retain certificates and eventually share an admitted ballot; required SAR and backup receipts and chain evidence are available. | WT proposal 6; resource limits | Decision recovery, closure or continued withdrawal stalls; limits may force fallback. | Explicit availability boundary |
| AR-85 | Profile and head dispatch reject bare, old-head and wrong-candidate WT transitions; history is admitted only as exact frozen evidence. | WT wire contract; proposal 7.4 | A retired WT or stale authorization can advance state. | Structural and abstract guard checks; interoperability pending |
| AR-86 | The originating Boomlet retains its own signed fragment until permanent setup retirement and reserves all journal and archive capacity before admission. | WT proposal 9; resource limits | Untrusted storage loss or exhaustion destroys recovery. | Specified; device endurance and fault testing pending |
| AR-87 | WT roster selection, payment, transport and legal arrangements provide useful diversity without unacceptable metadata exposure. | WT proposal 1, 3; architecture | Switching can preserve a common failure or reveal peer relationships. | External dependency |

### Boomletwo recovery requirements

These requirements apply to the [checkpoint candidate](boomlet_rollover.md).

| ID | Requirement | If missing | Status |
| --- | --- | --- | --- |
| AR-88 | Each recipient verifies both replacement signatures and atomically stores Boomletwo's accepted key and exact certificate before accepting future actions or acknowledging installation | A stale recipient mapping accepts actions under the predecessor identity or loses the replacement on restart | Specified in the lifecycle proposal; conformance pending |
| AR-89 | Recovery preserves exact obligations and decisions later than any supplied checkpoint, and cannot reduce required valid progress | Stale authentic state hides duress or votes; an independent redraw may finish early | Conservative threshold policies specified; complete-state recovery unresolved |



## Audit requirements


The controls below apply to [WT_FAILOVER_V1](README.md).
Their device and interoperability requirements must be audited separately from
the bounded models.

| Threat | Attack path | Required control and audit evidence | Risks |
| --- | --- | --- | --- |
| T-FAILOVER-01 | WT disappears with an undelivered padded commit; closure erases the withdrawal | Exact own SAR discharge before PREPARE, reviewed closure IDs, frozen obligation vector, final SAR receipt and any paired reset before cleanup; lost and duplicated acknowledgment tests | R-22, R-29 |
| T-FAILOVER-02 | A recipient restores a predecessor identity or recovery omits earlier votes | Preserve the designated backup, verify and persist its replacement certificate, require complete recovered voting history; certificate replay and hidden-vote cases | R-03, R-30 |
| T-FAILOVER-03 | Retired or returning WT replays a state-advancing signature | Versioned head wrapper, expected roster signer, candidate and active dispatch separation; negative vectors for every WT operation | R-10, R-31 |
| T-FAILOVER-04 | Candidate disappears after an honest COMMIT or a relay conceals the final certificate | Durable highest prepared certificate, immutable RECOVER, exact own report, higher promise, learnable final decision; candidate-loss model | R-13, R-30 |
| T-FAILOVER-05 | Export receipt causes erasure while Niso and WT lose or suppress the fragment | Originator retains exact bytes; verify the complete transaction, final SAR receipt and any paired reset before private cleanup; power interruption at every handoff | R-13, R-29 |
| T-FAILOVER-06 | Host floods proofs, skips ballots, or induces repeated writes and switch prompts | Early byte/count checks, trusted recovery allowance, idempotence, fixed reservations, elapsed SAR-delay lower bound; hardware timing and endurance tests | R-03, R-32 |
| T-FAILOVER-07 | Historical commit-set evidence admits new stale authorization or resets delay | Exact origin package and prior local gates; only listed age exceptions; retain mystery, counter, sequence, reached state and spacing floor | R-10, R-25, R-31 |
| T-FAILOVER-08 | Candidate selection exposes metadata or shares the failed provider's infrastructure | Candidate-only package disclosure, no private state, independent peer evidence retention; provider and operational review | R-16, R-28 |

### Designated Boomletwo activation checks

| Threat | Required evidence | Risks |
| --- | --- | --- |
| Four surviving peers conceal the missing peer's COMMIT or claim an arbitrary current WT | Hidden-vote counterexample; source-authenticated head required for read-only discovery | R-30, R-31 |
| Replacement is incomplete, substituted or lost during recipient installation | Both key fields, nested signatures, setup context, atomic accepted-key update and exact retry result | R-30 |
| Old checkpoint omits a later duty or vote | Complete-state recovery mechanism; authenticated history alone does not prove freshness | R-29, R-30, R-32 |
| Target substitution or private-policy changes bypass base security | Exact designated setup target and SAR, current consent state and counter under SPEC Section 16.7, checkpoint and one-time activation binding | R-01, R-19, R-30 |
| Device replacement drops duress state or lowers remaining work | Independent activation check, sticky stored duress, exact activation SAR receipt, earlier-duty recovery and conservative threshold; no raw redraw against restored credit | R-22, R-29 |
| Current recovery packets are withheld | Demonstrate that missing evidence stalls withdrawal recovery while retaining activation records, recorded duress and accepted recipient identities | R-29, R-30 |
