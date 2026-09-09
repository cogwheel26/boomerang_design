# Security verification

The current [Boomletwo candidate](boomlet_rollover.md) uses self-contained Ping
checkpoints and an offline backup, without a continuously online ST. Numerical
checks establish conservative threshold bounds in valid progress units and
expose unsafe independent redraws. They do not solve latest-state recovery or
old-source exclusion. WT decision and lifecycle experiments remain separate.

## Findings

| ID | Severity | Finding | Disposition |
| --- | --- | --- | --- |
| SV-01 | High | Authenticating one host ciphertext stream and decrypting a later stream admits unauthenticated bytes to CBC and parsing | Authenticate the exact checkpoint bytes before decryption; the retained capsule experiment checks that general ordering hazard |
| SV-02 | Medium | Cached signature validation does not bound repeated copying and decoding | Checkpoint schema, padding, retained-byte limits and recovery admission remain conformance work; experimental capsule budgets are not current limits |
| SV-03 | High | Colluding Niso, WT and four peers can report increasing fictitious heights | Open blocker for the real-chain delay guarantee; authenticated chain observation is required |
| SV-04 | Medium | Honest peers can lock different five-intent combinations and prevent completion | Explicit availability and forced-fallback risk; discarding locks would weaken decision safety |
| SV-05 | Medium | Checkpoint format, self-inclusive Pong dispatch and activation safeguards are not implementation-ready | Open conformance blocker; exact schemas, rejection rules, resource costs and independent vectors are required |
| SV-06 | Critical | A replacement path can preserve key exclusivity while weakening backup availability, private policy or coercion resistance | Preserve the designated backup and ordinary gates; independent redraw needs a conservative floor, while later-state recovery and source exclusion remain unresolved |

## Checkpoint security review

The base permits a designated encrypted setup backup and leaves activation open
in [SPEC Section 18.5](../spec/SPEC.md#185-boomletwo). The candidate keeps that
backup offline and uses source-signed, target-encrypted Ping checkpoints as
recovery evidence. It introduces no trusted recorder. Mutable checkpoint export
is limited to that target and cannot change immutable setup policy.

A new mystery applied to a restored counter is unsafe. In the explicit 1–100
example at counter 80, 80 of 100 independent draws would already be reached.
Using max(original mystery, new independent draw) preserves the original floor.
Using the setup upper bound plus the independent draw avoids carrying the original
mystery, with additional delay that must fit the fallback schedule.

These are bounds on valid counter progress. They do not permit counting old
Pongs, Ping sequence numbers or offline elapsed time as new progress. Stale
counters can withhold progress safely, but stale negative facts about duties
and votes can erase security obligations. The same authentic checkpoint can
precede no further activity, a concealed duress duty, a hidden COMMIT, or an
isolated source that remains usable. Peer replies cannot distinguish these
histories when every surviving peer is dishonest.

The [finite checks](boomlet_rollover_model.md) enumerate conservative threshold
bounds, the immediate-completion attack and a concurrent-draw example where a
finish probability of 1/4 becomes 7/16. Exclusion and complete-state recovery
remain required before backup signing or WT voting is enabled.

## WT security argument

One fixed logical peer remains honest throughout the relevant history. Its
active device enforces a durable journal and any activated backup must preserve
that same history. Four other peers may collude with Niso and WT and conceal
certificates for which the honest peer supplied a signature. Cryptographic
forgery and hash collisions are excluded. The enrolled ST, Iso and the honest
peer's fixed SAR have their base trusted roles.

### One decision per instance

Every valid final certificate includes the honest peer's COMMIT. That peer
retains the matching five-PREPARE certificate before exporting COMMIT. Every
recovery collection includes its immutable report and retained evidence.
Selecting the highest justified prepared value preserves any hidden final
decision. A first conflicting prepared certificate would also need that honest
peer's justified PREPARE. Promises block lower-ballot voting, and same-ballot
double voting is durably forbidden. Completed final decisions remain learnable.

The honest peer locks one five-intent combination before reporting or voting.
A new intent at the same predecessor requires final ABORT or withdrawal before
any PREPARE or RECOVER. A withheld activation COMMIT cannot coexist with an
unlocked replacement attempt. Tombstones survive cancellation and activation.

This protects decisions but cannot reconcile different first locks at two
honest peers. SV-04 remains an availability and coercion concern.

### Rescue and delay preservation

An initial activation PREPARE requires the honest signer's exact outstanding SAR
acknowledgment. Recovery retains that established witness. ABORT preserves
completed discharge. Pre-DIGGING closure cannot erase an initialized withdrawal;
initialized switches preserve mystery, counter and spacing state. Local fragments
remain retained, and private cleanup requires verified completion and finished
duties. These are state-preservation claims. They do not prove real elapsed block
progress when all observations available to the honest device are fabricated.

### WT lookup from a checkpoint

Collision resistance binds existing `WtReady` content to the checkpoint's WT
head, setup, predecessor, switch and roster index. Any holder can supply those
bytes. This authenticates the WT at that checkpoint; it does not establish the
head's currentness. Later decisions need their ordinary proofs and safe recovery
of the source's voting history, including any vote emitted after its last Ping.

## Reproducible evidence and limits

[security_model.md](security_model.md) retains the executable source and command.
The decision-checker dependency has SHA-256
`72578865ef2582351e6d7f9a4492a4c9441641d12a869822d675a33f697f878a`.
The model prints its digest. Re-running the experiments checks their explicit
abstractions, not conformance of an activation implementation.

| Search or check | Recorded result | Scope |
| --- | --- | --- |
| Decision core with three ballots | 127 states and 126 transitions | Authenticated voting abstraction |
| Candidate-loss recovery | 305 delivery cases | Retained prepared evidence and malformed-proof guards |
| Two competing intent combinations | 302 states and 603 transitions | No conflicting activation children; split locks can stall |
| Experimental decision and handoff ordering | 1,790 states and 4,982 transitions | Freeze, retirement, one activation and retained public state; does not model designated backup or coercion |
| Experimental capsule processing | 22 states and 72 transitions | Same-byte authentication and bounded copying; not a proposed post-setup export path |
| Local withdrawal lifecycle | 52 states and 134 transitions | Discharge, recorded delay state, completion and fragment retention |
| Five-peer snapshot matrix | 7,776 snapshots and 241,056 honesty assignments | Finite abstract preparation guards |
| Quiescence and acknowledgment bindings | 64 combinations and seven changed fields | Guard checks, not private-state decoding |
| Canonical WT lookup | 128 field and version variants | Matching a trusted pin, not establishing its freshness |
| Abstract release bindings | 256 substitutions | Exact tuple binding, not current activation wire conformance |
| Saved encoding fixtures | Two preimage hashes | No production signatures or encryption |

Fifteen negative controls expose missing prepared evidence, late COMMIT, intent
rebinding, hidden COMMIT at freeze, premature release, repeated state import,
source rollback, ciphertext substitution, unbounded copying, skipped discharge,
reset delay, acknowledgment rollback, receipt-only cleanup, fragment erasure
and peer-only cold recovery. These checks remain useful necessary conditions.
Their success cannot establish that a recovery design is no easier to attack
than the ordinary withdrawal path.

## Remaining attack boundaries

For SV-03, hold real height at 100 while compromised observers claim 101, 102
and 103 in otherwise valid Pings and current-head Pongs. With one-block spacing
and catch-up, local comparisons permit three counter increments. Genuine SAR
acknowledgments may arrive without another Bitcoin block. Observer agreement
and nondecreasing reports cannot establish real progress. The missing control
is authenticated chain evidence or an explicitly narrower observer assumption.

For SV-04, compromised peers give honest A and B different intent combinations.
Each locks and emits RECOVER for its own combination. Neither can collect both
honest reports, and neither intent is locally withdrawable. Lowering the report
threshold or allowing timeout-based unlock does not preserve the safety argument.

For SV-06, test target substitution, private-policy changes, old checkpoints,
independent redraw, repeated recovery attempts, hidden obligations, hidden votes
and concurrent use of an isolated source and its backup. The easiest route
to spending, suppressing rescue, reducing uncertainty or forcing predictable
fallback must be assessed against the base adversary. No complete lost-source
solution or assurance result is claimed.

Exact checkpoint and activation schemas, combined lifecycle and coercion analysis, full signed
and encrypted setup vectors, reorg handling, device fault tests and measured
resource admission remain required before adoption.
