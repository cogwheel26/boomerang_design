# Observed-consent integration security review

| Item | Value |
| --- | --- |
| Review date | 2026-09-19 |
| Status | Eight open findings; no fixes applied by this review |
| Scope | Consent options against the working-tree specification, dynamic rescue-data integration, setup and withdrawal contracts, and proposed Boomletwo lifecycle |
| Repository base | `7ddfd54c8d370caca0ad781cdc9c6cef04b4d48c` plus uncommitted changes |

## Review boundary

The [consent proposal](Cannon_observed_consent_decision_proposal.md) remains
**draft, not adopted**, and has no changes in the current working-tree diff.
The applied dynamic rescue-data changes and Boomletwo lifecycle proposal create
interfaces that a consent implementation must respect. The findings below are
integration risks and contract conflicts, not claims of exploits in a deployed
consent implementation.

Severity describes the consequence if the affected option is integrated without
closing the stated condition. Each finding identifies its applicable option;
options are alternatives, so they do not all need to be implemented. Several
blockers are already acknowledged in general terms by the proposal. This review
makes their interaction with the current files explicit rather than treating
those acknowledgments as completed controls.

## Findings

| ID | Severity | Affected choice | Issue |
| --- | --- | --- | --- |
| OCI-01 | High | Options 8 and 9 | A ceremony-bound verdict can be replayed between checks in the same withdrawal. |
| OCI-02 | High | Option 8 with the existing rescue root | Giving ST the rescue root also grants account-wide upload authority and historical decryption. |
| OCI-03 | High | Option 1 and any quarantine rollover exception | Destination restriction alone does not preserve withdrawal gates or the destination's protection. |
| OCI-04 | High | Fixed-set maintenance and full setup replacement | Quarantine lacks a defined atomic transition and a path for pending rescue obligations. |
| OCI-05 | High | Variants 4C and 4D, and lifecycle integration | Existing backup schemas and one-time provisioning rules cannot safely express reenrollment or replacement as local flags. |
| OCI-06 | Medium | Option 8; possibly Option 9 | ST-originated SAR ciphertext does not fit the current Boomlet-authenticated placeholder channel. |
| OCI-07 | High | Setup replacement after rescue-root compromise | A fresh setup with the same password and SAR preserves compromised rescue authority. |
| OCI-08 | Medium | Option 11 and any deliberate claim reduction | Consent alternatives and the new lifecycle requirements do not share one compatible acceptance profile. |

### OCI-01 A ceremony binding does not establish a fresh check

**Evidence.** Consent Options 8 and 9 specify a ceremony-bound receipt or verdict;
Option 9 also binds a consent epoch. [SPEC Section 16.2](../spec/SPEC.md)
requires an exact outstanding nonce and phase and rejects duplicate responses.
Repeated checks can occur within one approved withdrawal.

**Failure sequence.** Retain an authenticated safe result from the first check.
When a later check in the same withdrawal would indicate duress, suppress its
response and resubmit the earlier result. Its ceremony and epoch still match.
If those are the implemented acceptance conditions, the old safe classification
can satisfy the later check. An acknowledgment of the exact submitted ciphertext
proves delivery of that ciphertext, not freshness of the human interaction.

**Required closure.** Retain per-check binding to the outstanding nonce and phase,
expected authority and consent epoch, device and withdrawal scope, and exact
classification payload. Define one-time consumption, crash recovery, retries,
and cutover of pending checks during rotation. Challenge and epoch binding must
be authenticated through the entire verdict-to-SAR-acknowledgment chain.

**Acceptance case.** Two checks with different nonces in one withdrawal must not
accept each other's receipt or payload. Repeat with an epoch change, restart,
and an exact delivery retry. The small witness below confirms only that the
weaker binding cannot distinguish the two checks; the current nonce rule already
rejects this substitution.

### OCI-02 ST receives more authority than consent classification

**Evidence.** Option 8 explicitly gives ST `doxing_key_for_sar` if the placeholder
plaintext is retained. The applied [SPEC Section 9.4.1](../spec/SPEC.md) derives
both device-data keys and `dynamic_update_auth_key` from that root. Section
13.1.3 gives the account credential append authority under every device ID.

**Consequence.** A compromised ST holding this root can decrypt available retained
ciphertext and derive the registered upload credential. It can authenticate
misleading uploads under existing or new device IDs. Append-only retention stops
replacement of accepted entries, but does not attest which physical Phone sent
an observation or establish its truth. False authenticated observations can
therefore become durable rescue evidence. This is additional authority beyond
returning a consent verdict and is a concrete consequence of the dynamic-data
integration, not a failure of its KDF or CMAC.

**Required closure.** Make this expanded ST trust boundary an explicit decision.
Either keep the rescue root out of ST and design a narrowly scoped signaling
capability, or update provisioning, compromise recovery, data-access assumptions,
and rescue interpretation to account for ST's upload and decryption powers.
Moving classification alone cannot be described as preserving the current key
ownership boundary.

**Evidence obtained.** Using the focused dynamic-data checker and synthetic inputs,
a root holder generated an upload that passed account authentication and
successfully decrypted an existing vector. No live SAR or user data was involved.

### OCI-03 Restricted rollover can become a maintenance spending path

**Evidence.** Option 1 permits a quarantine exception bound to a verified new
descriptor and required peer approvals. Its adoption section correctly leaves
safe rollover unresolved. [SPEC Sections 15 and 16](../spec/SPEC.md) bind
ordinary spending to transaction review, approvals, SAR acknowledgment, digging,
and final signing conditions.

**Failure sequence.** A coercer induces the recovery path and obtains approval for
a replacement descriptor. If destination matching is treated as sufficient
permission to sign, the implementation can skip the ordinary delay and rescue
gates. Even transfer to another syntactically valid Boomerang descriptor needs
policy checks: replacement keys, milestone distances, fallback paths, fees,
change, and every output influence what protection remains after the transfer.

**Required closure.** Specify the exact old-setup signing authority, destination
policy, whole-transaction checks, and inherited delay and rescue obligations.
If any ordinary gate is deliberately replaced, state the substitute guarantee
and its assumptions. Include emitted old signatures, competing spends,
confirmation and reorganization rules, and funds still controlled by the old
setup. Destination restriction is one check, not evidence of equivalent safety.

**Acceptance case.** Reject a valid-looking destination with weakened policy,
unauthorized outputs, or an attempt to reach signing before the required gates.
Exercise fallback proximity and an old signed spend concealed until rollover.
This remains an acknowledged design blocker, not an implemented bypass.

### OCI-04 Quarantine can strand or race pending rescue work

**Evidence.** OC-SR-08 requires in-place maintenance outside withdrawal; the common
limits require preservation of pending rescue. [SPEC Section 18.2](../spec/SPEC.md)
keeps stalled ceremonies bound to their state, and Sections 16.3–16.4 deliver
placeholders through withdrawal traffic. The lifecycle draft likewise requires
outstanding duties to be resolved before planned handover.

**Failure sequence.** Disclosure is reported while a withdrawal is stalled or a
duress-bearing message is awaiting acknowledgment. A maintenance handler that
interprets the absence of active processing as an idle ceremony can race a
withdrawal transition. A quarantine handler that simply stops all withdrawal
traffic can also retain a pending duty in storage without ever delivering it.
A fresh enrollment or later safe response must not clear that earlier duty.

**Required closure.** Define an authenticated, durable quarantine transition and
its ordering with outstanding checks, commitments, placeholder delivery, and
signing output. Distinguish stalled state from a closed ceremony. Specify how
rescue delivery and exact acknowledgments continue while ordinary spending is
blocked, and how restart preserves both duties and quarantine. Define who can
request quarantine so that an unauthenticated host report does not silently
create a new way to disable every peer's ordinary path.

**Acceptance case.** Interrupt disclosure handling before and after a duress
response, placeholder send, acknowledgment, and signing handoff. Race maintenance
against withdrawal entry. No test may lose a pending rescue obligation, advance
unauthorized signing, or substitute a later safe check for earlier duress.

### OCI-05 Backup flags do not implement consent exclusion

**Evidence.** Variant 4C proposes `CONSENT_REENROLL_REQUIRED`; Variant 4D retires a
backup before local rotation and provisions another. Current
[`BoomletBackupState`](../spec/wire_catalog.json) requires a five-element
`duress_consent_set`, with no specified consent-mode or consent-epoch field.
[SPEC Section 13.10](../spec/SPEC.md) marks a completed backup and rejects another
backup for the same active state. Activation and revocation remain open in
Section 18.5. The lifecycle proposal expresses requirements, not those
missing enforcement mechanisms.

**Failure sequence.** Encoding an empty set as a reenrollment flag conflicts with
the existing schema. Using a normal-looking dummy set or a host-only flag can
leave a legal safe answer unless every activation and check path enforces the
new mode. Separately, clearing `backup_complete` to implement replenishment can
permit another exported copy while the first target or an issued activation
receipt still exists. An offline backup retains its copied consent and authority.

**Required closure.** Define a versioned protected consent mode, freshness and
history requirements, inactive-device gates, and the device-bound transition
that excludes each former target. Specify legacy import, exact retry, lost
`BackupDone`, and conflicting-target behavior. Update the schema and all
consumers together. A locally reset flag is not evidence of remote retirement.

**Acceptance case.** Try legacy imports, dummy and empty sets, restored old state,
missing acknowledgments, and delayed activation receipts after replacement.
Require explicit enrollment and source exclusion before any new authority is
usable. Catalog inspection confirmed the schema mismatch; no backup activation
implementation exists here to test this end to end.

### OCI-06 The placeholder channel assumes a Boomlet sender

**Evidence.** Option 8 returns a SAR-encrypted classification from ST. It already
notes a placeholder-authentication change, but gives no replacement contract.
[SPEC Sections 9.4, 9.6, and 16.3–16.4](../spec/SPEC.md) use directional
Boomlet-to-SAR keys tied to the logical Boomlet and selected SAR identities.
SAR's replay record and acknowledgment also use that Boomlet identity.

**Consequence.** Ciphertext created under an ST-to-SAR channel cannot be inserted
unchanged into the existing placeholder field and verified as Boomlet traffic.
Honest implementations fail closed. Removing sender checks or sharing the
Boomlet's channel secrets with ST to make the message pass would create a new
identity and authority weakness. Possession of the rescue root alone does not
supply the current channel keys.

**Required closure.** Choose and specify the relay, nested envelope, or replacement
channel model, including sender enrollment, exact context, replay key, payload
size, acknowledgment coverage, and late-message handling. Update Boomlet, WT,
SAR, ST, and their conformance profile together. Option 9 needs the same analysis
if its verifier originates the SAR ciphertext.

**Acceptance case.** Verify that a payload from the selected consent authority
reaches SAR through the defined channel, while another ST, SAR, device, setup,
check, or profile is rejected without relaxing the base identity checks.

### OCI-07 Fresh setup does not automatically retire rescue credentials

**Evidence.** Option 1 can replace exposed keys through full setup replacement.
[SPEC Section 13.1](../spec/SPEC.md) derives the SAR root and lookup identifier
from the password and selected SAR key, without a setup ID. Section 9.4.1 derives
the upload credential using the registration profile and identifier; Section
13.1.3 explicitly retains old holders' append authority. A fresh device ID
separates history but does not revoke an account credential.

**Failure sequence.** After compromise of a Phone, a root-bearing ST under Option
8, or another holder of the rescue root, rebuild the custody setup while reusing
the same doxing password and SAR. Under the same registration profile, the
rescue root, identifier, and upload credential remain the same. Retiring the
custody devices does not stop the former root holder from authenticating uploads
or decrypting newly obtainable ciphertext under that root.

**Required closure.** Distinguish consent-only exposure from root or credential
compromise in the recovery procedure. If rescue authority was exposed, define
its replacement and account transition, including retention and correct routing
for still-active old setups. Do not silently replace the old account key or
history, which the dynamic lifecycle forbids. A profile change alone is not a
specified account-migration mechanism.

**Acceptance case.** Rebuild with the same password and SAR and demonstrate that
the old credential remains valid; then test the explicitly chosen replacement
procedure. Receipt and history access for old obligations must remain intact.
Observation of a consent answer alone does not imply root compromise; this
finding applies only when that additional secret was exposed.

### OCI-08 Alternative consent guarantees conflict with an unconditional lifecycle gate

**Evidence.** Consent Option 11 explicitly replaces SAR release and concealment
rules; the proposal allows broader alternatives to replace fixed-set and
unchanged-wire properties. In contrast,
[BW-SR-08](Cannon_boomletwo_lifecycle_proposal.md#bw-sr-08-confidentiality-and-duress-observability) unconditionally
requires the existing SPEC Sections 16.4–16.6 observability contract. The lifecycle
proposal also presents preserved SAR behavior as a core requirement.

**Consequence.** Adopting mandatory visible review while treating all existing
lifecycle requirements as satisfied produces an inconsistent conformance claim.
A replacement backup could also be provisioned under a different understanding
of its signaling, clearance, and rescue obligations. Option 2's explicit reduced
protection likewise must not be counted as satisfying fixed-set recovery's
OC-SR-01.

**Required closure.** Before adoption, select a consent profile and map every
consent and lifecycle requirement to retained, replaced, or explicitly lost
properties. Define its version and compatibility rules. A privacy or availability
tradeoff must appear in the normative claim and test plan, not just in an
option's disadvantages.

**Acceptance case.** Produce one internally consistent requirements matrix for
the selected option and reject cross-profile import or activation. Unselected
alternatives may remain drafts; their mutually incompatible claims must not be
combined into one passing checklist.

## Evidence and limits

The review compared the consent options with the applied rescue-data KDFs,
account authority, backup schema, current challenge rules, placeholder channel,
withdrawal failure behavior, and the new lifecycle requirements. It did not
modify those source documents or perform a general audit of every repository
change.

Three bounded checks were run: an omitted-nonce replay witness, root-derived
upload authentication and decryption using the focused checker, and backup
catalog inspection. Reproduce them from the repository root:

```sh
python3 -B - <<'PY'
from pathlib import Path
import json
import sys
sys.path.insert(0, str(Path('scripts').resolve()))
from check_dynamic_rescue import auth_key, make_upload, validate_upload, decrypt_payload, tagged

old = {'withdrawal': 'W', 'epoch': 7, 'nonce': 'N1', 'phase': 'initial'}
next_check = {'withdrawal': 'W', 'epoch': 7, 'nonce': 'N2', 'phase': 'repeated'}
assert all(old[k] == next_check[k] for k in ('withdrawal', 'epoch'))
assert not all(old[k] == next_check[k] for k in next_check)
print('W1: ceremony-only acceptance cannot distinguish these checks')

vectors = json.loads(Path('spec/dynamic_rescue_vectors.json').read_text())
root = bytes.fromhex(vectors['inputs']['doxing_key_for_sar'])
account = tagged('Boomerang/doxing_data_identifier', root)
upload, _ = make_upload(root, account, b'\x91'*32, b'\x92'*32,
                        b'synthetic misleading observation', b'\x93'*16)
validate_upload(upload, auth_key(root, account))
known = vectors['vectors'][0]
assert decrypt_payload(root, bytes.fromhex(known['upload'])) == bytes.fromhex(known['payload_hex'])
print('W2: rescue-root holder derives upload and decryption authority')

catalog = json.loads(Path('spec/wire_catalog.json').read_text())
backup = next(s for s in catalog['schemas'] if s['name'] == 'BoomletBackupState')
consent = next(f for f in backup['fields'] if f['name'] == 'duress_consent_set')
assert consent['required']
assert consent['exact_items']['constant'] == 'duress_selection_count'
assert 'consent_mode' not in [f['name'] for f in backup['fields']]
print('W3: existing backup schema has a required set and no consent-mode field')
PY
```

These checks use synthetic test data and the checker's explicit test profile.
W1 is a binding counterexample, not an implementation test. W2 validates the
additional cryptographic authority, not real SAR admission or rescue behavior.
W3 checks the current schema, not device firmware. No consent implementation,
hardware rollback, real storage failure, human ceremony, or timing experiment
was tested. Existing dynamic-data vector success does not close these findings.

## Reviewed source fingerprints

SHA-256 identifies the reviewed working-tree bytes, since the changes are not
represented by one committed revision. A changed file needs its affected
findings rechecked. The tracking files updated by this review are excluded.
OCI-04, OCI-05, and OCI-08 were rechecked against the consolidated Boomletwo
proposal on 2026-09-22; their conclusions are unchanged.

| File | SHA-256 |
| --- | --- |
| `proposals/Cannon_observed_consent_decision_proposal.md` | `bd8d6b9be0639641edee746ab4d23b81b470d44fcd7194728a7354effe6806b0` |
| `proposals/Cannon_boomletwo_lifecycle_proposal.md` | `4abd642e9d7cc649ac83487705b5ac32961fe3b7382e12a848cf88f7bfd7e367` |
| `spec/SPEC.md` | `86f8baab945b5b6f72a20558f8029da2eec914e176bfe21b20c4ece9154c30e9` |
| `spec/wire_catalog.json` | `122df5d7d1e33f6e71497cb8576b65d7b0f862949c909b21919e976c85b98dd1` |
| `scripts/check_dynamic_rescue.py` | `a9c9d81b940dcf021d82f19ce6d01683764a25d98d39ffba409dd8be8170d176` |
| `setup/setup_development_contracts.md` | `2720b7150fed2601b1ee1bfd57f3558e46d635a6919a8f4ff495daf8af0e7f14` |
| `withdrawal/withdrawal_development_contracts.md` | `933cb43a36b25972a49464811145cfdb6762c4063dbfbb3f414846f2f58b4bef` |
