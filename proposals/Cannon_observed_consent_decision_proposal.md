# Observed-consent decision proposal

| Item | Value |
| --- | --- |
| Status | Draft, not adopted |
| Phase 1 priority | 2 |
| Normative baseline | [`SPEC.md`](../spec/SPEC.md) at `ed91233a4216be0c96f8f8d081276b7c94a39751` |
| Related gaps | DG-38, AR-35, AR-79, FM-30, R-12, R-21 |

## Current status

Each user chooses one unordered five-country `duress_consent_set` during setup.
Boomlet stores the set, the user memorizes it, and the setup backup copies it
into Boomletwo. Every later duress check treats that same set as safe.

Fresh challenge permutations and nonces prevent replay of the encrypted ST
response, but they do not change the answer. A coercer who observes the ST
display and one legitimate safe selection learns an answer that remains valid
for the life of the setup. The protocol cannot detect that observation.

No consent replacement, version, revocation, or recovery procedure exists.
The Boomletwo activation procedure is also unresolved, so a change that only
updates the active Boomlet can leave the observed set usable after recovery.

## Roadmap goal

> Decide whether a setup may remain active after its consent set is observed.
> Record the outcome as a setup-replacement requirement, a protocol change, an
> accepted limitation, or a production blocker.

## Decision boundary

An observed-consent event includes any known or reasonably suspected case in
which an attacker could have learned or dictated a safe selection. It includes
recording the ST display and input, attacker-operated input under the user's
guidance, ST compromise, and extraction of the stored set from either Boomlet.

The decision addresses later ceremonies. No rotation can restore the secrecy
of a response during a ceremony that the attacker is already observing. That
ceremony has lost the duress distinction and must be abandoned when doing so is
safe. If abandonment is unsafe or impossible, the protocol provides no rescue
assurance for that ceremony.

The decision does not assume that observation will be detected. Periodic
rotation can shorten exposure after an unnoticed event, but continuous
observation defeats each newly displayed set.

## Required properties

Any option proposed for production must state how it meets these properties.

| ID | Property |
| --- | --- |
| OC-SR-01 | A known or suspected observed set is not accepted by any device that can later become active. |
| OC-SR-02 | At most one set is accepted by an active Boomlet. Transition overlap must not preserve the observed set as a second valid answer. |
| OC-SR-03 | Crash, retry, message loss, and rollback cannot reactivate an invalidated set. Ambiguous state fails closed. |
| OC-SR-04 | Boomletwo recovery cannot restore an observed set or bypass a required fresh enrollment. |
| OC-SR-05 | Consent maintenance cannot activate signing authority or weaken the one-active-Boomlet invariant. |
| OC-SR-06 | Enrollment and rotation use the trusted ST path, two fresh nonce-bound confirmation rounds, and an environment in which observation is not suspected. |
| OC-SR-07 | A rotation transcript, receipt, counter, or public commitment does not enable offline recovery of the low-entropy five-country set. |
| OC-SR-08 | Withdrawal messages, SAR handling, and safe and duress observability remain unchanged. Rotation occurs outside a withdrawal. |
| OC-SR-09 | The user can determine which set is current without trusting Niso or accepting a rollbackable host display. |
| OC-SR-10 | Every terminal state has an operator action, including lost active device, stale backup, interrupted rotation, and unavailable witness. |

Rotation is a compromise-recovery action, not proof that a prior interaction
was private. A rotation performed while observed or dictated is itself a new
observed-consent event.

## Option 1: Immutable set with mandatory setup replacement

`duress_consent_set` remains unchangeable within a setup. Known or suspected
observation compromises the setup. Operators stop ordinary withdrawals and
replace the complete setup, including fresh consent enrollment and movement of
funds to the new descriptor.

The old setup remains exposed until rollover confirms. A controlled rollover
may use the old setup only in an environment where the observed answer cannot
be exploited. The replacement procedure must define the affected peer set,
safe abandonment of an active withdrawal, milestone constraints, confirmation
requirements, and retirement of both old Boomlet devices.

Because observation is external to the protocol, quarantine begins through an
explicit maintenance action. Its authority, trusted display, durable Boomlet
state, and recovery behavior must be defined. A Niso-only flag is insufficient
because a compromised or rolled-back host could hide it. The marker cannot be
cleared within the old setup.

### Benefits

- Smallest protocol change and easiest rule to audit.
- No mutable consent state, version synchronization, or rotation rollback.
- Boomlet and Boomletwo continue to contain the same setup-scoped state.
- A fresh setup also replaces other setup-bound material that may have been
  exposed with the consent set.

### Costs and limits

- One peer's observed response can require all peers to coordinate and move
  funds.
- Exposure persists during setup creation and on-chain rollover.
- Frequent suspected observation can make the custody arrangement impractical.
- Safety depends on a complete, rehearsed rollover procedure that does not yet
  exist.
- It cannot help an in-progress coerced ceremony.

This option resolves the roadmap decision as a setup-replacement requirement.
DG-38 remains open until the replacement and rollover path is specified and
tested.

## Option 2: Immutable set with accepted exposure

The setup remains usable after known observation and continues accepting the
same set. Procedures may recommend shielding, monitoring, or voluntary setup
replacement, but the protocol imposes no invalidation rule.

This option accepts that the coercer can force all later checks to evaluate as
safe. It conflicts with OC-SR-01 and leaves the central concealed-duress claim
unavailable for that setup. Operational privacy does not repair the protocol
property after disclosure.

This option is unsuitable for a production profile that claims recovery from
known consent observation. If adopted, the limitation must be prominent and
DG-38 must remain an accepted critical risk. If that risk is not explicitly
accepted, the setup is a production blocker.

## Option 3: Paired rotation synchronized to Boomletwo

The active Boomlet enrolls a fresh set and transfers an authenticated,
setup-bound update to the designated inactive Boomletwo. Both devices commit
the same new consent epoch before the rotation is declared complete.

A viable design needs at least:

- a monotonic `consent_epoch` and setup-bound state hash;
- target-bound encryption for the update;
- durable prepare, commit, and abort states on both devices;
- idempotent response replay after message loss;
- rollback-resistant evidence of the committed epoch;
- proof that Boomletwo remains unable to sign while accepting the update;
- recovery rules for loss of either device at every transition; and
- secure erasure of the old set without accepting old and new sets together.

There is no atomic write across two offline secure elements. A two-device
exchange alone cannot tell a recovered Boomletwo whether the active device
committed before it was lost. An independent durable witness or a recovery
rule that treats every interrupted rotation as compromised is required.

### Benefits

- The user memorizes one set shared by the active and backup devices.
- Boomletwo can be immediately ready after a completed rotation.
- A successful rotation preserves the existing descriptor and setup-bound
  service registrations.

### Costs and limits

- Every rotation requires safe access to both devices and the trusted ST.
- The same critical secret remains present on two devices.
- Crash consistency, stale-backup recovery, and rollback add a distributed
  state transition to the secure-element protocol.
- A missing or damaged Boomletwo can prevent rotation or leave the setup
  compromised.
- The design depends on the unresolved Boomletwo lifecycle and cannot be
  accepted before the one-active-device invariant is enforceable.

## Option 4: Independent Boomlet and Boomletwo consent state

The active Boomlet can enroll a fresh set without copying it to Boomletwo.
Boomletwo must never fall back to an imported or previously observed active
set. Three variants satisfy that rule differently.

### Variant 4A: Same set entered independently

The user performs separate enrollment ceremonies on Boomlet and Boomletwo and
enters the same fresh set on each. No consent secret moves directly between
the devices.

This removes the secret-transfer message but not the synchronization problem.
If only one ceremony completes, one device still accepts the observed set. A
user assertion cannot prove to either device that the other committed the same
set. A public equality commitment would expose the set to exhaustive search,
while a protected device-to-device equality proof recreates a paired update
protocol. The design also needs a durable rule for which device is updated
first and what happens if the second device is lost.

This variant is no safer than Option 3 unless incomplete maintenance
irreversibly makes Boomletwo ineligible for activation. With that rule, it has
the delayed-recovery behavior of Variant 4C without its simpler state model.

### Variant 4B: Distinct pre-enrolled sets

Boomlet and Boomletwo each receive a different set during a secure setup or
maintenance ceremony. The user memorizes both and selects the set for the
currently active device.

This avoids synchronized secret updates, but doubles the memorized material
and creates a dangerous device-selection error. Entering the other device's
valid set produces a duress signal rather than a recoverable mismatch. Both
sets also require independent compromise tracking and rotation. This variant
should not proceed without human-factors evidence showing an acceptably low
false-duress rate under stress.

### Variant 4C: Enrollment required on activation

Boomletwo does not import a usable consent set. Its backup state records
`CONSENT_REENROLL_REQUIRED`. After the old active Boomlet is irreversibly
deactivated and the one-active-device proof succeeds, the recovering device
must complete fresh two-round ST enrollment before it can enter an active,
withdrawal-capable state.

An active Boomlet may rotate its own set through the same two-round enrollment
while idle. Rotation invalidates the old set in one durable local transition.
Boomletwo requires fresh enrollment on every activation, so it needs neither
the active set nor its latest epoch.

### Benefits

- No cross-device consent synchronization or shared consent secret.
- Loss of the active Boomlet does not restore its observed set.
- The user memorizes only the set for the active device.
- Local rotation has a smaller crash and rollback surface than paired update.

### Costs and limits

- Boomletwo is not immediately withdrawal-ready after device recovery.
- Recovery requires the trusted ST and a private enrollment environment.
- Recovery attempted during coercion must fail closed because safe enrollment
  cannot be established.
- The option depends on a completed Boomletwo activation and deactivation
  protocol and changes the meaning of a ready backup.
- Local rotation still needs monotonic durable state so a device rollback
  cannot restore its own old set.

Variant 4C is the strongest in-place rotation candidate because it avoids the
need to make an offline backup current. It trades emergency readiness for a
smaller secret and synchronization surface.

## Option 5: Derived rotating sets with a witnessed epoch

Boomlet and Boomletwo share a protected consent-rotation root and derive the
set for a monotonic epoch. An independent service records the latest committed
epoch so Boomletwo can recover it without contacting a lost active device. The
user learns and confirms each derived set through ST.

The witness must not receive a plain hash of the set. The set has only
`C(193, 5)` possibilities, so an unkeyed commitment permits exhaustive
recovery. Witness records must contain only an opaque, domain-separated value
and authenticated monotonic state.

This approach reduces transferred secret data but does not remove distributed
commit. The protocol must order user confirmation, witness commit, and local
activation so that no crash makes an unknown set current. Witness rollback or
unavailability must fail closed. Compromise of the shared derivation root can
expose multiple epochs, and witness authority adds another setup-bound
dependency.

The option merits research only if immediate Boomletwo readiness is required
and paired secret updates prove unacceptable.

## Option 6: Challenge-dependent safe responses

A separate trusted mechanism could derive a different safe answer for every
fresh challenge. Observation of one answer would then provide no reusable
answer. Candidate mechanisms include a personal authenticator, a protected
user secret entered into ST, or a pre-generated one-time sequence.

Each candidate changes the human duress model. A coercer may compel use of the
authenticator, observe the entered secret, seize the one-time material, or
force the user to identify the safe path. Pre-generated sequences also need
backup synchronization and rollback protection. No candidate in the current
design preserves the simple memorized covert choice with adequate usability
evidence.

This is a replacement for the consent mechanism, not a small rotation change.
It belongs in longer-term research unless a concrete design passes coercion
and human-factors review.

## Rotation triggers

Known or suspected observation requires immediate quarantine under every
rotation option. Scheduled maintenance can limit the lifetime of an unnoticed
observation, but its interval must be justified against ceremony burden,
memory errors, secure-element endurance, and the period of residual exposure.

Automatic rotation inside a withdrawal is unsuitable. A classification-
dependent prompt could reveal whether the preceding answer meant safe or
duress, and an observing coercer could learn the replacement set. Any rotation
must be a separate maintenance ceremony whose messages and displays are not
part of the safe and duress observability contract.

## Comparative evaluation

| Option | Rejects an observed set on all future devices | Boomletwo readiness | User burden | State complexity | Main unresolved dependency |
| --- | --- | --- | --- | --- | --- |
| 1. Immutable with replacement | Yes, after confirmed rollover | New backup created with new setup | Learn one new set | Low in device protocol, high operationally | Safe full-setup rollover |
| 2. Immutable with accepted exposure | No | Unchanged | None | Low | Explicit acceptance of failed duress distinction |
| 3. Paired synchronized rotation | Yes, after atomic completion | Immediate | Learn one new set | High | Crash-safe one-active Boomletwo lifecycle |
| 4A. Same set entered independently | Yes, only after both updates complete | Immediate | Repeat enrollment on both devices | High | Partial updates and unproven set equality |
| 4B. Distinct pre-enrolled sets | Yes, if both remain uncompromised and current | Immediate | Memorize two sets | Medium | Human error and per-device compromise tracking |
| 4C. Enrollment on activation | Yes | Delayed until enrollment | Learn one current set | Medium | Safe activation and private recovery ceremony |
| 5. Derived sets with witnessed epoch | Yes, if witness state is current | Immediate when witness is available | Learn one new set | High | Witness authority, commit ordering, root protection |
| 6. Challenge-dependent response | Potentially | Design dependent | Design dependent | Very high | New duress mechanism and human-factors evidence |

No option addresses an unnoticed observation until a replacement or rotation
occurs. No option withstands continuous observation of every consent ceremony.

## Proposed Phase 1 disposition

Adopt Option 1 for Specification v1.0. A consent set is immutable within its
setup, and known or suspected observation makes that setup ineligible for
ordinary withdrawal. The setup must be replaced and funds rolled into a fresh
descriptor as soon as a safe ceremony can be conducted. Option 2 is not an
acceptable silent fallback. If the replacement procedure cannot meet its
safety and timing requirements, observed-consent compromise remains a
production blocker.

Retain Variant 4C as the preferred protocol-change candidate if evaluation
shows that full setup replacement is operationally unacceptable. It should be
designed together with Boomletwo activation rather than adding a separate
synchronization protocol. Paired rotation and witnessed derivation should be
reconsidered only if immediate backup readiness is a demonstrated requirement.

This disposition does not claim that setup replacement is complete. It selects
the security rule and makes the missing rollover procedure an explicit
dependency.

## Evaluation plan

### Replacement path

Measure and exercise:

- detection-to-quarantine and quarantine-to-confirmed-rollover time;
- coordination required from unaffected peers;
- behavior when a withdrawal is already active;
- behavior near every fallback milestone;
- loss or unavailability of either Boomlet device during replacement;
- transaction fee, confirmation, and service-registration failure; and
- retirement evidence for old Boomlet, Boomletwo, WT, and SAR state.

Option 1 is acceptable only if the runbook, reference harness, and tabletop
exercise show that a fresh setup and fund rollover can complete within the
selected operating bounds without relying on the exposed set in an attacker-
observed environment.

### Rotation candidates

Any in-place design must be modeled and tested for:

- observation before, during, and after rotation;
- old-set entry after successful rotation;
- loss of each message and receipt;
- power loss before and after every durable write;
- rollback to every prior epoch or local state;
- active Boomlet loss during rotation;
- activation of a stale Boomletwo;
- attempted use of both devices;
- witness outage or equivocation where applicable;
- user entry of a set associated with the wrong device; and
- false-duress rates during normal, fatigued, and stressed operation.

The tests must prove that a successful terminal state accepts only the new set,
an unsuccessful or ambiguous state cannot claim recovery, and no update path
grants signing authority.

## Application checklist

If Option 1 is adopted, the following tracked material requires change.

| Tracked files | Required change |
| --- | --- |
| `spec/SPEC.md` | State that consent is immutable within a setup; define the authority and durable marker for setup compromise; prohibit ordinary withdrawal; reference the required fresh-setup rollover and affected active-ceremony behavior. |
| `DESIGN.md`, `README.md`, `GLOSSARY.md` | Replace the setup-lifetime assumption with the compromise and replacement rule; retain the limits for unnoticed and continuous observation. |
| `security_models/README.md`, `security_models/architecture.md` | Record the disposition, rollover dependency, exposure window, and production-blocker condition. |
| `security_models/assumption_register.md`, `security_models/attack_trees.md`, `security_models/audit_mappings.md` | Replace AR-79 with the adopted response and add failure paths for delayed or unsafe replacement. |
| Setup and withdrawal documentation | Define rejection or abandonment behavior for a setup marked consent-compromised and ensure no diagram implies in-place rotation. |
| New ADR | Record immutability, mandatory replacement, rejected options, and the conditions that would reopen in-place rotation. |
| Operator runbooks and reference harness | Specify quarantine, replacement, rollover, old-state retirement, crash recovery, evidence, and test scenarios. |

PlantUML sources change only if normative message or state behavior changes.
SVG files are not regenerated.

## Acceptance

The observed-consent milestone is complete only when reviewers explicitly
choose one roadmap disposition and its required dependencies are either
implemented or recorded as production blockers.

For the proposed disposition, acceptance requires:

- normative setup-scoped immutability;
- a mandatory response to known or suspected observation;
- a durable quarantine marker entered through trusted maintenance authority;
- no ordinary withdrawal after quarantine;
- a complete fresh-setup and fund-rollover procedure;
- safe handling of an already active withdrawal;
- retirement of both old consent-bearing devices;
- reproducible rollover and failure tests; and
- documentation that unnoticed and continuous observation remain outside the
  recovery guarantee.
