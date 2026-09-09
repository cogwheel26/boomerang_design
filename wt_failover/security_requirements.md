# Proposed security-model integration

These controls and assumptions accompany the WT failover and designated Boomletwo
activation proposals. Adoption must incorporate them into the architecture,
assumption register, threat model, operational controls and conformance plan.
The base security-model documents remain separate from these proposals.

AR-82 through AR-89 and R-29 through R-32 are proposed integration identifiers.
R-29 covers lost rescue obligations or recovery artifacts; R-30 covers conflicting
authority or decisions; R-31 covers stale WT authority and replay; R-32 covers
resource exhaustion. Other identifiers refer to the base security model.

## Architecture


[WT_FAILOVER_V1](README.md) selects a fresh setup and wire version.
Exactly one roster WT has authority at a certified head. Candidate transport
carries preparation evidence; it acquires live coordination authority only after
a five-COMMIT decision is installed. Peer relays remain untrusted. Each Boomlet
checks its own snapshot, obligation, votes, current head and phase locally.

The original Boomlet is initially the only active authority for its identity.
The designated Boomletwo retains the base authenticated setup backup with its
peer keys inactive. The setup export exception stays closed after completion.
Both devices require non-rollbackable lifecycle state. A host MAC, public archive,
peer vote or WT certificate cannot recover an unseen source vote. Safe activation
after source loss and resistance to forced fallback remain adoption requirements.

Frozen placeholder discharge uses the existing end-to-end SAR channel and exact
ordinary acknowledgment. All honest signers finish that duty before preparing
activation, including withdrawal closure. ABORT preserves completed discharges.
The chosen SAR and its processing assumptions stay fixed. Five reached Pings
are accompanied by the recipient's exact acknowledgment before signing.

Niso and WT store public reconstruction packages and fragments. Boomlet retains
its own fragment through completion until permanent setup retirement. Full
transaction verification and own completed duties close the active ceremony;
a holder's storage receipt alone cannot authorize erasure. Bounded journal,
archive and parsing reservations limit load and can reduce availability.

Fresh WTs receive peer identities, setup parameters, approved transaction
artifacts and public progress only when needed for the selected scope. Repeated
switches expose service relationships and correlated timing. They cannot prove
provider independence or future SAR availability. Mystery, counter, consent
answers and placeholder plaintext remain inside the established trusted devices.

### Self-contained Ping recovery

[Boomletwo recovery](boomlet_rollover.md) retains the original designated
backup offline. Encrypted mutable-state checkpoints bind only that device and
the existing setup policy. No long-lived key is reexported, no target can be
reenrolled, and ST has no continuous recording role.

An authentic checkpoint can provide conservative progress and a WT head at that
point. It cannot prove latest state, absence of later rescue duties or votes,
or exclusion of the old source. Those remain activation requirements. The same
counter cannot be applied unmodified against a fresh lower mystery. The proposed
floors are max(original mystery, independent draw), or upper bound plus independent
draw when the original mystery is not retained. Neither policy provides fencing.

All ordinary review, duress, exact SAR discharge, chain, replay and signing gates
still apply. An old reached flag alone cannot establish that later duties are
complete. Delay inequalities count valid progress units; they do not justify
historical-Pong replay or unverified elapsed-height credit.

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
| AR-82 | At least one honest identity has one active device, an inactive designated setup backup and enforceable non-rollbackable lifecycle and protocol journals. | WT proposal 3.3, 6 | Clones or restored hidden votes permit conflicting decisions. | Required device admission; hardware evidence pending |
| AR-83 | Each honest signer retains exact frozen placeholder bytes and verifies its own acknowledgment before initial activation PREPARE. | WT proposal 5.2, 7.3 | Closure or candidate loss can discard rescue delivery. | Specified; bounded lifecycle checks |
| AR-84 | All five peers cooperate, retain certificates and eventually share an admitted ballot; required SAR and chain evidence is available. | WT proposal 6; resource limits | Decision recovery, closure or continued withdrawal stalls; limits may force fallback. | Explicit availability boundary |
| AR-85 | Profile and head dispatch reject bare, old-head and wrong-candidate WT transitions; history is admitted only as exact frozen evidence. | WT wire contract; proposal 7.4 | A retired WT or stale authorization can advance state. | Structural and abstract guard checks; interoperability pending |
| AR-86 | The originating Boomlet retains its own signed fragment until permanent setup retirement and reserves all journal and archive capacity before admission. | WT proposal 9; resource limits | Untrusted storage loss or exhaustion destroys recovery. | Specified; device endurance and fault testing pending |
| AR-87 | WT roster selection, payment, transport and legal arrangements provide useful diversity without unacceptable metadata exposure. | WT proposal 1, 3; architecture | Switching can preserve a common failure or reveal peer relationships. | External dependency |

### Boomletwo recovery requirements

These requirements apply to the [checkpoint candidate](boomlet_rollover.md).

| ID | Requirement | If missing | Status |
| --- | --- | --- | --- |
| AR-88 | The original source cannot issue conflicting new authority after backup activation, even if merely isolated | Two devices can sign conflicting decisions or offer parallel completion opportunities | Exclusion mechanism unresolved |
| AR-89 | Recovery preserves exact obligations and decisions later than any supplied checkpoint, and cannot reduce required valid progress | Stale authentic state hides duress or votes; an independent redraw may finish early | Conservative threshold policies specified; complete-state recovery unresolved |



## Audit requirements


The controls below apply to [WT_FAILOVER_V1](README.md).
Their device and interoperability requirements must be audited separately from
the bounded models. Every path also maps to DG-41.

| Threat | Attack path | Required control and audit evidence | Risks |
| --- | --- | --- | --- |
| T-WT-01 | WT disappears with an undelivered padded commit; closure erases the withdrawal | Exact own SAR discharge before PREPARE, reviewed closure IDs, frozen obligation vector; lost and duplicated acknowledgment tests | R-22, R-29 |
| T-WT-02 | Source and stale backup cosign incompatible histories | Preserve the one designated setup backup; require exclusive activation and complete state continuity; hidden-vote counterexample and device fault tests | R-03, R-30 |
| T-WT-03 | Retired or returning WT replays a state-advancing signature | Versioned head wrapper, expected roster signer, candidate and active dispatch separation; negative vectors for every WT operation | R-10, R-31 |
| T-WT-04 | Candidate disappears after an honest COMMIT or a relay conceals the final certificate | Durable highest prepared certificate, immutable RECOVER, exact own report, higher promise, learnable final decision; candidate-loss model | R-13, R-30 |
| T-WT-05 | Export receipt causes erasure while Niso and WT lose or suppress the fragment | Originator retains exact bytes; verify complete transaction and own duties before private cleanup; power interruption at every handoff | R-13, R-29 |
| T-WT-06 | Host floods proofs, skips ballots, or induces repeated writes and switch prompts | Early byte/count checks, trusted recovery allowance, idempotence, fixed reservations, elapsed SAR-delay lower bound; hardware timing and endurance tests | R-03, R-32 |
| T-WT-07 | Historical commit-set evidence admits new stale authorization or resets delay | Exact origin package and prior local gates; only listed age exceptions; retain mystery, counter, sequence, reached state and spacing floor | R-10, R-25, R-31 |
| T-WT-08 | Candidate selection exposes metadata or shares the failed provider's infrastructure | Candidate-only package disclosure, no private state, independent peer evidence retention; provider and operational review | R-16, R-28 |

### Designated Boomletwo activation checks

| Threat | Required evidence | Risks |
| --- | --- | --- |
| Four surviving peers conceal the missing peer's COMMIT or claim an arbitrary current WT | Hidden-vote counterexample; source-authenticated head required for read-only discovery | R-30, R-31 |
| Source remains usable while backup activates | Enforceable exclusion under an isolated-source attack; peer promises are insufficient | R-30 |
| Old checkpoint omits a later duty or vote | Complete-state recovery mechanism; authenticated history alone does not prove freshness | R-29, R-30, R-32 |
| Target substitution or private-policy changes bypass base security | Exact designated setup target, unchanged consent and SAR, checkpoint and one-time activation binding | R-01, R-19, R-30 |
| Device replacement drops duress state or lowers remaining work | Exact duty continuity and conservative threshold; no raw redraw against restored credit | R-22, R-29 |
| Captor isolates source or withholds current packets | Demonstrate source-loss recovery without concurrent authority or lost duties; compare attack cost with ordinary withdrawal | R-29, R-30 |
