# Boomletwo recovery from self-contained Pings

A self-contained Ping can carry the state needed to interpret and resume a
DIGGING checkpoint. Boomletwo can remain offline while peers, WT and Niso retain
the packet. ST participates in its ordinary user interactions and an eventual
recovery review, with no continuous recording duty.

This is a useful transport and DIGGING-state mechanism. A complete activation
protocol must additionally prevent concurrent source authority and account for
security events later than the supplied checkpoint. The rules below distinguish
what the packet proves from those unresolved requirements. Activation assumes
the original Boomlet is unavailable; it never requests its cooperation.

## 1. Packet and setup binding

Keep the one designated Boomletwo authorized by the base setup backup, its
normal-key authorization, Iso checks and `BackupDone`. Pin that target's
bootstrap identity and the immutable setup policy. Recovery cannot select an
arbitrary target or change ST, SAR, normal key, consent set or descriptor.

A recovery-capable Ping bundle contains:

- the ordinary Ping header and exact encrypted SAR placeholder;
- a bounded checkpoint encrypted and authenticated directly to the designated
  Boomletwo, using the existing ECDH and CBC-CMAC construction;
- a commitment to that ciphertext inside the Ping's existing signed content.

The ciphertext is a detached part of the same bundle. The commitment lets peers
forward the signed Ping without copying a large private checkpoint into every
collection. The bundle itself includes the bytes, not only a URL or hash. Any
holder can supply it, but no holder gains recovery authority.

Bind the encryption to the profile, setup, designated target, approved withdrawal
ID, Ping sequence and checkpoint format. The signed header, checkpoint and exact
placeholder must agree on those bindings. Use fresh IVs; exact retries preserve
the original bytes. Authenticate the exact retained ciphertext before decryption.

The checkpoint contains the actual counter, initialized status, original mystery
if the selected delay policy uses it, reached flag, height and spacing floors,
peer sequence and reached-state checks, active WT head and index, exact current
SAR duty, accepted duress state and required challenge state. It also binds the
approved transaction and the evidence needed for its current phase. All private
fields stay encrypted. A Ping sequence is not a counter: valid no-advance Pongs
still generate Pings in the base protocol.

Construct the new placeholder and the checkpoint before signing the Ping. The
checkpoint represents the state associated with that output, with explicit next
sequence and pending acknowledgment. It must not embed the signature, ciphertext
or digest of the complete packet containing itself. Required header fields and
placeholder bytes provide the binding without a recursive hash definition.
Store only bounded state and references to supplied evidence, not nested earlier
checkpoint packets. Exact field layout and size limits remain conformance work.

The existing Ping signature covers the added commitment; a second source
signature solely for the checkpoint is unnecessary. Its WT-neutral recovery
context survives a WT change. Current WT authority still uses the ordinary
head-bound WT signature and channel checks.

## 2. Including the recipient's own Ping in Pong

If “self-inclusive” also means returning a peer's own Ping to it, the Pong can
contain one ordered collection of all five signed Pings. WT can sign that common
Pong content once, while recipient encryption and each recipient's exact SAR
acknowledgment remain separate. This is a proposed change from the base's five
recipient-specific four-Ping collections.

Require exactly one Ping from each setup peer in canonical peer order, including
the recipient in its own slot. Missing, repeated or substituted identities fail.

During ordinary operation, Boomlet requires its returned Ping to match the exact
one it retained. That comparison can avoid an additional self-signature check.
During recovery, Boomletwo verifies the original Boomlet signature and checkpoint
binding instead. It still verifies the other four signatures and their ordinary
sequence, reached-state and freshness conditions.

Counter advancement continues to test the other four peers. Adding the own Ping
to that freshness predicate would change the lagging-peer catch-up behavior.
An old self Ping and its historical Pong are evidence, not a newly received Pong
that earns another counter increment. Exact SAR discharge remains mandatory.

The change saves common WT signing work but adds an own-Ping header to each
recipient's collection. Detached checkpoints avoid multiplying private-state
payloads across those collections. These are proposed wire changes, requiring
consistent version-selected handlers; they cannot be mixed with the base shape.

## 3. An independently generated mystery

Let `c` be the authenticated saved counter, `M` the original mystery, and `R`
a new independent draw by Boomletwo. For an unreached checkpoint, `c < M`.

Installing `R` as the threshold while restoring `c` is unsafe. With a draw from
1 through 100 and `c = 80`, 80 percent of replacements would immediately become
reached. Even excluding draws at or below `c` can shorten the actual remaining
work and gives a second completion opportunity if the source still exists.

There are two useful policies:

| Policy | Effective recovery threshold | Consequence |
| --- | --- | --- |
| Retain an encrypted original floor | `T = max(M, R)` | The new draw is independent, but recovery never lowers this withdrawal's original threshold |
| Do not carry the original mystery | `T = U + R`, where `U` is the setup-fixed upper bound on `M` | Recovery has an independent threshold above every possible original draw, at the cost of additional delay |

Both restore the authenticated `c` and require subsequent valid progress until
that counter reaches `T`. For the first policy,

```text
remaining_recovery = max(0, max(M, R) - c)
remaining_original = max(0, M - c)
remaining_recovery >= remaining_original
```

For the second, `U + R >= M`. Checked arithmetic and a setup-selected extended
counter range are required. The extra delay must fit the fallback planning
budget; making deterministic fallback more likely would undermine the purpose.
The first policy is the smaller change. The second meets a strict requirement
that the effective recovery threshold be independent of the original draw.

Generate `R` once after the exact checkpoint and recovery attempt have been
irrevocably bound. Persist it before any observable result. Retries, power loss,
a different peer response or a later snapshot cannot trigger another draw for
that attempt. No preview, diagnostic or trial-activation interface exposes its
value or whether a candidate draw would finish early.

An authenticated reached checkpoint proves that the old threshold was met at
that point. It does not prove that later rescue duties are absent or authorize
signing by itself. A new delay must not silently regress an already published
reached flag in the same Ping stream; any such policy needs explicit incarnation
semantics. The formulas above apply to an unreached checkpoint.

Starting an entirely new counter at zero with a full fresh draw is a different
policy. Under the base uniform draw, with the source truly gone, it can be slower
in distribution than the remaining old game. It does not establish exclusive
authority, preserve the exact realized delay, or recover pending obligations.
Neither that policy nor the two thresholds above completes activation by itself.

## 4. What a saved Ping proves

| Claim | Supported by a valid packet? |
| --- | --- |
| The designated source authenticated these bytes for this setup and withdrawal | Yes, under its signature and encryption checks |
| The source had accepted at least the checkpoint's recorded progress | Yes, under the base honest-device assumption |
| This packet names the WT head at that checkpoint | Yes |
| This is the last Ping or the currently installed WT head | No |
| No later duress challenge, placeholder, vote or signing output exists | No |
| The source is destroyed or unable to continue | No |

A stale counter is a lower bound and can conservatively withhold progress.
Missing rescue duties, replay tombstones and hidden WT votes cannot be treated
as harmless lost progress. A complete signed packet authenticates a snapshot,
not a negative claim about everything that happened afterward.

For example, the host may retain a safe checkpoint, suppress a later Ping with
an undelivered duress placeholder, and present the safe checkpoint at recovery.
The source could also have emitted a WT COMMIT after its last Ping; four peers
can conceal that vote and its final certificate. Recovering “no pending vote”
from the old packet could then create a conflicting decision.

Covering more fields inside the Ping does not cover events between Pings.
Checkpointing every security output improves recoverable evidence, but untrusted
holders can still conceal the newest checkpoint. A chain proves ancestry, not
that no signed successor exists.

## 5. Peer WT discovery

Peers may supply the `WtReady` record matching the checkpoint's WT head. Verify
its canonical setup, scope and roster index, then use the existing commitments:

```text
ready_commitment = H("Boomerang/wt/candidate_ready", ready_record)
lookup_head = H("Boomerang/wt/activation",
  ready_record.scope.setup_instance_id,
  ready_record.scope.previous_head,
  ready_record.scope.switch_id,
  ready_commitment)
require lookup_head == checkpoint.active_wt_head
```

`H` uses the setup's existing WT profile. One matching record suffices without
fresh peer signatures. It proves the WT identity at that checkpoint. A newer
head requires the ordinary authenticated decision history and recovery rules;
choose neither the greatest claimed index nor the majority's assertion.

A fresh challenge to all four survivors authenticates their present responses,
not their completeness or truthfulness. When the lost device belonged to the
only honest peer, every survivor can lie. Discovery cannot supply the missing
source vote or establish exclusive activation.

## 6. Activation requirements beyond the Ping

The source-loss declaration must be safe even when an attacker has isolated,
rather than destroyed, the original Boomlet. Merely naming a new incarnation
or asking peers to ignore the old one is insufficient when those peers collude.
Both devices otherwise retain the same logical signing authority.

Independent redraws make that risk concrete. If two independent remaining-delay
samples each finish within a period with probability `p`, allowing either result
to win gives probability `1 - (1 - p)^2`. At `p = 1/4`, that is `7/16` instead
of `1/4`. Conditional redraws do not remove the benefit of concurrent trials.
Preserving the original threshold as a floor addresses threshold reduction;
it does not prove global exclusion or prevent conflicting WT histories.

Before enabling signing or WT voting on Boomletwo, a complete design must supply:

- an enforceable exclusion mechanism for the old device's new authority;
- a rule for later or concealed rescue duties, decisions and replay state;
- authenticated reconstruction of the selected transaction and required evidence;
- one-time activation, replay protection and fresh local signing nonces;
- unchanged ordinary review, SAR and DIGGING gates, plus the inherited chain
  observation assumptions and a conservative recovery progress floor.

Historical Pongs cannot be replayed to earn fresh progress. Recovery must not
convert offline elapsed time, Ping count, checkpoint selection or speculative
height catch-up into extra counter increments. The exact fresh-progress and
incarnation rules require specification before using the numerical delay bound
as a claim about elapsed time. The base authenticated-chain issue remains open.

The self-contained-Ping mechanism does not require a continuously online ST or
backup. It also does not currently provide the first two guarantees above under
the one-honest-peer model. They remain explicit design requirements, not an
assumption that the source kindly stops. No activation command is authorized
solely by the checkpoint or peer reports.

## 7. Cost and verification

The candidate adds one bounded private-state encryption and signed commitment
to a Ping, with no extra source signature. A full five-Ping Pong can share its
WT signature across recipients. Normal Boomlet self-Ping validation can use
exact retained-byte comparison; recovery performs source verification and one
checkpoint decryption. ST has no recurring recording role, and Boomletwo has no
normal-operation power or connectivity requirement.

These savings concern transport and DIGGING recovery only. The snapshot format,
byte limits, holder availability, incarnation rules and complete activation
mechanism are not finalized. State must stay confidential, valid safe and duress
bundles must have the same padded shape, and no decoder may import arbitrary
private policy or restore secret signing nonces.

The [bounded checks](boomlet_rollover_model.md) demonstrate threshold bounds,
redraw counterexamples and stale-checkpoint indistinguishability. They do not
prove a complete activation protocol. The [sequence](09_boomlet_rollover.puml)
shows packet preparation and guarded recovery, with unresolved activation
requirements explicit.
