# Executable security model

The current self-contained-ping checks are in
[boomlet_rollover_model.md](boomlet_rollover_model.md). The activation search
checks Boomletwo's independent duress and SAR gates, certificate persistence and
seven recipient identity updates. Signatures are authenticated abstractions.
The capsule experiment checks general ordering hazards. Its version string is a
test fixture, not an additional selected protocol version.

This bounded model checks protocol ordering with one continuously honest logical
peer and four adversarial cosigners. Signatures and storage protection are
authenticated abstractions. The existing decision checker supplies the voting
state machine; its source digest is printed with the results. The additional
model source is retained below as part of the proposal.

Run from the repository root with Python 3.10 or later. This creates no files and
does not render diagrams.

```sh
python3 -B - <<'PY'
from pathlib import Path
document = Path('wip and stale/proposals/wt_failover/security_model.md').read_text()
source = document.split('```python\n', 1)[1].split('\n```', 1)[0]
exec(compile(source, 'wip and stale/proposals/wt_failover/security_model.md', 'exec'))
PY
```

The searches exhaust their reachable finite graphs. Crash and duplicate actions
preserve committed state. Ambiguous physical writes must lock the device; their
hardware implementation is outside the model. The inherited voting search
allows ballot jumps as a conservative enlargement of the proposal's
successor-only rule. It uses three ballots and every justified recovery choice.

The intent search admits two competing five-intent combinations sharing the
honest peer's intent. The activation search starts from Boomletwo's stored
backup and models both initial duress flags, both answer results, exact SAR
discharge, certificate commitment and delivery to seven recipients. A later
ordinary operation requires independently validated withdrawal history. Exact
retries preserve that later private state.
The capsule search permits arbitrary host substitution, interrupted copies and
replays, with two complete copy attempts. A third copy is reachable only in its
negative control. Six snapshot classes per peer produce 7,776 lifecycle cases;
each is checked under all 31 nonempty sets of honest peers.

These bounds do not cover all successive identity replacements, arbitrary
message schedules, the complete transaction parser or physical side channels. See the
[verification report](security_verification.md) for the security argument,
findings and remaining work.

```python
from collections import deque
from dataclasses import dataclass, field, replace
from hashlib import sha256
from itertools import product
from pathlib import Path
import json
import runpy

decision_path = Path('outside/scripts/check_wt_switch_decision.py')
decision = runpy.run_path(str(decision_path), run_name='decision_model')
Vote = decision['SafetyState']
vote_steps = decision['safety_steps']
NONE = decision['NONE']
ACTIVATE = decision['ACTIVATE']
ABORT = decision['ABORT']


def search(initial, steps, violation):
    queue = deque(initial)
    parents = {s: None for s in initial}
    edges = 0
    while queue:
        state = queue.popleft()
        reason = violation(state)
        if reason:
            trace = []
            cursor = state
            while parents[cursor] is not None:
                cursor, action = parents[cursor]
                trace.append(action)
            return len(parents), edges, reason, list(reversed(trace))
        for action, successor in steps(state):
            edges += 1
            if successor not in parents:
                parents[successor] = state, action
                queue.append(successor)
    return len(parents), edges, None, []


def check(name, initial, steps, violation, negative=False):
    states, edges, reason, trace = search(initial, steps, violation)
    if negative:
        assert reason, f'Undetected negative control {name}'
        print(f'NEGATIVE {name}: {reason}')
        print('  ' + ' -> '.join(trace))
    else:
        assert reason is None, (name, reason, trace)
        print(f'PASS {name}: {states} states, {edges} transitions')


def finals(vote):
    return set(vote.committed) - {NONE}


@dataclass(frozen=True)
class Intents:
    votes: tuple = field(default_factory=lambda: (Vote(), Vote()))
    locked: int = -1
    withdrawn: bool = False


def intent_steps(state, mutant=None):
    if not state.withdrawn and all(v == Vote() for v in state.votes):
        yield 'withdraw before any report or vote', replace(state, withdrawn=True)
    for instance, vote in enumerate(state.votes):
        if state.locked not in (-1, instance) and mutant != 'rebind':
            continue
        for action, new_vote in vote_steps(vote):
            if state.withdrawn and new_vote.prepared[0] == ACTIVATE:
                continue
            votes = list(state.votes)
            votes[instance] = new_vote
            yield f'combination {instance}: {action}', replace(
                state, votes=tuple(votes), locked=instance)
    yield 'crash or duplicate preserves intent journal', state


def intent_violation(state):
    if any(len(finals(v)) > 1 for v in state.votes):
        return 'conflicting final values in one combination'
    if sum(ACTIVATE in finals(v) for v in state.votes) > 1:
        return 'two certified activation children at one predecessor'
    if state.withdrawn and any(ACTIVATE in finals(v) for v in state.votes):
        return 'withdrawn intent activated'


@dataclass(frozen=True)
class Activation:
    phase: int = 0  # inactive, query saved, answered, placeholder saved, receipt, active
    saved_duress: bool = False
    duress: bool = False
    mismatch: bool = False
    placeholder: int = -1
    receipt: bool = False
    certificate: bool = False
    published: bool = False
    installed: int = 0  # Seven recipients: four peers, ST, WT and SAR.
    acknowledged: int = 0
    stale_action: bool = False
    recovered: bool = False
    progress: bool = False
    history: int = 0


def activation_steps(state, mutant=None):
    if state.phase == 0:
        yield 'retain activation query and fixed key pair', replace(state, phase=1)
    if state.phase == 1:
        for mismatch in (False, True):
            duress = mismatch if mutant == 'clear_activation_duress' else state.saved_duress or mismatch
            yield 'consume ST answer durably', replace(
                state, phase=2, mismatch=mismatch, duress=duress)
    if state.phase == 2:
        yield 'retain exact activation placeholder', replace(
            state, phase=3, placeholder=int(state.duress))
    if state.phase == 3:
        yield 'verify exact activation SAR acknowledgment', replace(
            state, phase=4, receipt=True)
    if state.phase == 4:
        yield 'atomically commit ACTIVE and complete certificate', replace(
            state, phase=5, certificate=True)
    if state.phase in (2, 3) and mutant == 'early_certificate':
        yield 'commit certificate before SAR acknowledgment', replace(
            state, phase=5, certificate=True)
    if state.phase == 5 and not state.published:
        yield 'publish retained replacement certificate', replace(state, published=True)
    if state.published:
        for recipient in range(7):
            bit = 1 << recipient
            if not state.installed & bit:
                installed = state.installed if mutant == 'ack_before_key' else state.installed | bit
                yield f'recipient {recipient} stores key and certificate before acknowledgment', replace(
                    state, installed=installed, acknowledged=state.acknowledged | bit)
            elif mutant == 'accept_predecessor':
                yield 'authorize replayed predecessor-key action as new', replace(
                    state, stale_action=True)
            elif mutant == 'recipient_rollback':
                yield 'restore predecessor recipient mapping', replace(
                    state, installed=state.installed & ~bit)
    if state.phase == 5 and not state.recovered:
        # Complete withdrawal evidence is a prerequisite, not established by a certificate.
        yield 'validate required withdrawal history and duties', replace(state, recovered=True)
    if state.phase == 5 and state.recovered and not state.progress:
        yield 'complete later ordinary operation', replace(state, progress=True, history=1)
    if state.progress and mutant == 'reinstall_certificate':
        yield 'duplicate certificate reinstalls old private state', replace(state, history=0)
    yield 'crash or exact retry preserves activation and recipient journals', state


def activation_violation(state):
    if (state.saved_duress or state.mismatch) and not state.duress:
        return 'activation answer cleared recorded duress'
    if state.phase == 5 and not (state.receipt and state.certificate):
        return 'activation committed without exact SAR receipt and certificate'
    if state.phase >= 3 and state.placeholder != int(state.duress):
        return 'activation placeholder lost recorded duress'
    if state.published and not (state.phase == 5 and state.certificate):
        return 'certificate published before durable activation'
    if state.acknowledged & ~state.installed:
        return 'acknowledged recipient lost its replacement identity'
    if state.stale_action:
        return 'recipient accepted a new action under the predecessor key'
    if state.progress and not state.recovered:
        return 'withdrawal progressed without recovered evidence'
    if state.history != int(state.progress):
        return 'duplicate certificate rolled back later private state'


@dataclass(frozen=True)
class Capsule:
    host: int = 0  # 0 exact authenticated envelope, 1 substituted bytes
    stored: int = -1
    phase: int = 0  # 0 awaiting copy, 1 copied, 2 authenticated, 3 decoded
    used: int = 0
    copies: int = 0
    decrypted: int = -1


def capsule_steps(state, mutant=None):
    yield 'host substitutes its stored envelope', replace(state, host=1-state.host)
    if state.phase == 0 and state.copies < 3:
        if state.used < 2 or mutant == 'unbounded_copy':
            yield 'consume attempt and copy bounded envelope', replace(
                state, stored=state.host, phase=1, used=state.used+1,
                copies=state.copies+1)
    if state.phase == 1:
        if state.stored == 0:
            yield 'authenticate exact retained envelope', replace(state, phase=2)
        else:
            yield 'reject authentication without decryption', replace(
                state, phase=0, stored=-1)
    if state.phase == 2:
        decrypted = state.host if mutant == 'late_compare' else state.stored
        yield 'decrypt and parse capsule', replace(
            state, phase=3, decrypted=decrypted)
    if state.phase in (1, 2):
        yield 'interruption consumes attempt', replace(state, phase=0, stored=-1)
    yield 'duplicate or completed-state reboot', state


def capsule_violation(state):
    if state.decrypted not in (-1, 0):
        return 'unauthenticated substituted bytes reached decryption'
    if state.copies > 2:
        return 'host exceeded the complete-copy write budget'


@dataclass(frozen=True)
class Withdrawal:
    initialized: bool = False
    approved: bool = True
    has_backup: bool = False
    rotation_record: bool = False
    duty: int = 0
    acknowledged: bool = False
    frozen: bool = False
    prepared: bool = False
    decision_done: bool = False
    fragment: bool = False
    exported: bool = False
    transaction: bool = False
    closing: bool = False
    final_received: bool = False
    reset_done: bool = False
    duress: bool = True
    closed: bool = False
    delay: tuple = (0, 0, 0)  # mystery, counter, inherited floor


def withdrawal_steps(state, mutant=None):
    if state.duty == 1:
        yield 'verify exact own SAR acknowledgment', replace(
            state, duty=2, acknowledged=True)
    if not state.closed and not state.decision_done and not state.frozen:
        yield 'freeze exact withdrawal snapshot', replace(state, frozen=True)
    if state.frozen:
        if state.duty != 1 or mutant == 'skip_discharge':
            yield 'prepare activation', replace(state, prepared=True)
        if state.prepared:
            delay = (0, 0, 0) if mutant == 'reset_delay' else state.delay
            yield 'install certified activation', replace(
                state, frozen=False, prepared=False, decision_done=True,
                closing=state.closing or not state.initialized, delay=delay)
        duty = 1 if mutant == 'abort_rollback_ack' and state.acknowledged else state.duty
        yield 'install certified ABORT', replace(
            state, frozen=False, prepared=False, decision_done=True, duty=duty)
    if not state.closed and not state.frozen and state.initialized and not state.closing:
        if state.duty != 1 and not state.fragment:
            # Reached, PSBT and fresh signing-session checks are abstracted.
            yield 'retain fragment before exporting', replace(
                state, fragment=True, exported=True)
        if state.fragment:
            yield 'verify complete signed transaction', replace(state, transaction=True)
            if state.duty != 1 and (state.transaction or mutant == 'receipt_cleanup'):
                yield 'begin final cleanup', replace(state, closing=True)
    if state.closing and not state.closed and not state.frozen:
        if not state.approved:
            yield 'clean up before approval; retain duress', replace(
                state, closed=True, duress=mutant != 'clear_preapproval_duress')
        else:
            if state.duty != 1 and not state.final_received:
                # Abstracts saving the final ping and verifying its exact SAR receipt.
                yield 'verify saved final-ping receipt', replace(state, final_received=True)
            paired_reset = state.has_backup and state.rotation_record
            if state.final_received and paired_reset and not state.reset_done:
                yield 'verify exact paired reset acknowledgment', replace(state, reset_done=True)
            if ((state.final_received or mutant == 'skip_final_receipt')
                    and (not paired_reset or state.reset_done or mutant == 'skip_backup_reset')):
                yield 'complete cleanup and clear private state', replace(
                    state, closed=True, duress=False, delay=(0, 0, 0))
    if state.fragment and mutant == 'erase_fragment':
        yield 'storage receipt permits fragment erasure', replace(state, fragment=False)
    yield 'crash or retry preserves withdrawal journal', state


def withdrawal_violation(state):
    if state.prepared and state.duty == 1:
        return 'activation prepared with an undischarged honest obligation'
    if state.acknowledged and state.duty == 1:
        return 'ABORT restored an acknowledged obligation'
    if state.initialized and not state.closed and state.delay != (13, 7, 9):
        return 'switch reset initialized delay state'
    if state.closed and state.initialized and not state.transaction:
        return 'private cleanup accepted a receipt without a complete transaction'
    if state.closed and state.approved and not state.final_received:
        return 'approved withdrawal cleaned up without its final SAR receipt'
    if state.closed and state.has_backup and state.rotation_record and not state.reset_done:
        return 'cleanup skipped the configured backup reset'
    if state.closed and not state.approved and not state.duress:
        return 'pre-approval cleanup cleared sticky duress'
    if state.exported and not state.fragment:
        return 'untrusted storage caused loss of the local fragment'


def lifecycle_checks():
    # Each class is (initialized, duty), with duty 0 absent, 1 outstanding,
    # 2 exactly acknowledged. Byzantine peers may claim any of these classes.
    classes = tuple(product((False, True), range(3)))
    cases = 0
    rejected = 0
    for rows in product(classes, repeat=5):
        close = not any(initialized for initialized, _ in rows)
        for honest_mask in range(1, 32):
            honest = [i for i in range(5) if honest_mask & (1 << i)]
            can_prepare = all(rows[i][1] != 1 for i in honest)
            if not can_prepare:
                rejected += 1
            else:
                for i in honest:
                    initialized, duty = rows[i]
                    assert duty != 1
                    assert not close or not initialized
            cases += 1
    assert cases == 7776 * 31 and rejected > 0
    print(f'PASS lifecycle: 7776 snapshots, {cases} honesty assignments, '
          f'{rejected} preparation barriers')
    # Exact acknowledgment matching rejects a changed field, even if signed.
    expected = ('setup', 'peer', 'SAR', 'approved', 'IV', 'envelope', 'context')
    for field_index in range(len(expected)):
        wrong = list(expected)
        wrong[field_index] += '_other'
        assert tuple(wrong) != expected
    # Six independent non-quiescent conditions; only the empty set admits a move.
    assert sum(not any(flags) for flags in product((False, True), repeat=6)) == 1
    print('PASS acknowledgment binding: 7 substitutions; quiescence: 64 cases')


def peer_ping_checks():
    # Other protocol checks remain mandatory. None denotes explicit absence
    # of a signed ping in the frozen manifest.
    def above_frozen_sequence(withdrawal, sequence, bound):
        bound_withdrawal, frozen_sequence = bound
        return (withdrawal != bound_withdrawal or frozen_sequence is None
                or sequence > frozen_sequence)

    cases = (
        (7, 8, False),
        (8, 8, False),  # Pre-freeze ping withheld from a receiver last seeing 7.
        (9, 8, True),
        (10, 8, True),
        (0, None, True),  # Lagging peer's normal initial ping.
        (0, 0, False),
        (1, 0, True),
        (9, 9, False),  # Another activation raises the frozen bound.
        (10, 9, True),
    )
    for sequence, frozen_sequence, expected in cases:
        assert above_frozen_sequence('A', sequence, ('A', frozen_sequence)) == expected
    # A later withdrawal starts at zero under the same WT head.
    assert above_frozen_sequence('B', 0, ('A', 8))
    print(f'PASS peer ping freshness: {len(cases) + 1} sequence and scope cases')


def split_lock_boundary():
    # Three Byzantine peers show different intent material to honest A and B.
    # Each honest peer locks a different combination and emits RECOVER. Both
    # reports are durable, so neither intent can be withdrawn locally.
    locks = {'A': 0, 'B': 1}
    for combination in (0, 1):
        honest_reports = {peer for peer, lock in locks.items() if lock == combination}
        assert honest_reports != {'A', 'B'}
    print('BOUNDARY split locks: later cooperation cannot supply either five-report collection')


def fabricated_height_boundary():
    # Example positive parameters: spacing 1, catch-up 1, tolerance 0.
    # All other checks, including exact real SAR acknowledgments, are satisfied.
    # Niso, WT and four cosigners collude; no real block arrives during the run.
    real_height = last_seen = previous_pong = 100
    counter, mystery = 0, 3
    for claimed_height in (101, 102, 103):
        other_pings = (claimed_height,) * 4
        assert claimed_height >= previous_pong + 1
        assert claimed_height >= last_seen
        if claimed_height > last_seen and all(h == claimed_height for h in other_pings):
            counter += 1
        last_seen = min(claimed_height, last_seen + 1)
        previous_pong = claimed_height
    assert counter == mystery and real_height == 100
    print('BOUNDARY chain source: 3 counter increments with zero real block advances')


def u16(value):
    return value.to_bytes(2, 'big')


def text_value(value):
    raw = value.encode('ascii')
    return b'\x21' + len(raw).to_bytes(4, 'big') + raw


def b32(value):
    assert len(value) == 32
    return b'\x23' + value


def record(schema, *fields):
    return (b'\x40' + u16(schema) + u16(1) + u16(len(fields))
            + b''.join(u16(i+1) + value for i, value in enumerate(fields)))


def H(version, tag, *fields):
    tag_hash = sha256(tag.encode('ascii')).digest()
    encoded = b'\x31' + u16(len(fields)+1) + text_value(version) + b''.join(fields)
    return sha256(tag_hash + tag_hash + encoded).digest()


def lookup(version, setup, previous, switch, index, mode, obligation):
    scope = record(31, b32(setup), b32(previous), b32(switch))
    absent = record(32, b'\x01', b32(bytes(32)))
    ready = record(36, scope, b'\x10' + bytes([index]), b'\x10' + bytes([mode]),
                   absent, absent, b32(obligation))
    commitment = H(version, 'Boomerang/wt/candidate_ready', ready)
    return H(version, 'Boomerang/wt/activation', b32(setup), b32(previous),
             b32(switch), b32(commitment))


def binding_checks():
    version = 'boomerang-wt-rollover-1'
    fields = (version, bytes([17])*32, bytes([34])*32, bytes([51])*32,
              1, 0, bytes([68])*32)
    expected = lookup(*fields)
    choices = ((version, 'boomerang-wt-1'),
               (fields[1], bytes([18])*32), (fields[2], bytes([35])*32),
               (fields[3], bytes([52])*32), (1, 2), (0, 2),
               (fields[6], bytes([69])*32))
    accepted = [row for row in product(*choices) if lookup(*row) == expected]
    assert accepted == [fields]
    assert expected != H(version, 'Boomerang/wt/genesis', b32(fields[1]))
    catalog = json.loads(Path('wip and stale/proposals/wt_failover/wire_catalog.json').read_text())
    schema_names = {s['id']: s['name'] for s in catalog['schemas']}
    assert {i: schema_names[i] for i in (31, 32, 36, 44)} == {
        31: 'WtScope', 32: 'WtOptionalId', 36: 'WtReady', 44: 'WtHeadContent'}
    base_catalog = json.loads(Path('wip and stale/wire_catalog.json').read_text())
    assert len(schema_names) == len(catalog['schemas'])
    assert set(schema_names).isdisjoint(s['id'] for s in base_catalog['schemas'])
    fixtures = json.loads(Path('wip and stale/proposals/wt_failover/canonical_vectors.json').read_text())
    schema_ids = {s['name']: s['id'] for s in catalog['schemas']}
    for fixture in fixtures:
        body = bytes.fromhex(fixture['canonical_hex'])
        preimage = bytes.fromhex(fixture['signature_preimage_hex'])
        assert body[0] == 0x40
        assert int.from_bytes(body[1:3], 'big') == schema_ids[fixture['type'].split('<', 1)[0]]
        assert preimage.endswith(body)
        assert sha256(preimage).hexdigest() == fixture['preimage_sha256']
    print('PASS checkpoint-pinned WT discovery: 128 variants')
    print(f'PASS saved encoding fixtures: {len(fixtures)} preimage hashes')


def cold_recovery_counterexample():
    # Four adversaries complete every honest vote. The backup omits the
    # source's hidden ACTIVATE commitment and reports NONE in a higher ballot.
    prior_peer = decision['Peer'](0, True)
    peers = [prior_peer] + [decision['Peer'](i, True) for i in range(1, 5)]
    for peer in peers:
        peer.prepare(ACTIVATE, peers, candidate_available=True)
    qc = decision['Certificate']('prepare', 0, ACTIVATE)
    prior_peer.retain(qc, peers)
    prior_peer.commit(0)
    recorded_commit = prior_peer.committed[0]
    del prior_peer, peers
    backup = decision['Peer'](0, True)
    recovered = [backup] + [decision['Peer'](i, True) for i in range(1, 5)]
    reports = tuple(peer.recover(1) for peer in recovered)
    for peer in recovered:
        peer.prepare(ABORT, recovered, reports)
    qc_abort = decision['Certificate']('prepare', 1, ABORT)
    backup.retain(qc_abort, recovered)
    backup.commit(1)
    assert recorded_commit == ACTIVATE and backup.committed[1] == ABORT
    print('NEGATIVE peer-only cold recovery: hidden source ACTIVATE and backup ABORT')


def main():
    print('Decision source SHA256 ' + sha256(decision_path.read_bytes()).hexdigest())
    states, edges, conflict = decision['safety_search']()
    assert conflict is None
    print(f'PASS decision core: {states} states, {edges} transitions')
    for mutant in ('omit_highest', 'allow_old_commit'):
        _, _, trace = decision['safety_search'](mutant)
        assert trace
        print(f'NEGATIVE {mutant}: ' + ' -> '.join(trace))
    assert decision['recovery_cases']() == 305
    decision['rejection_cases']()
    print('PASS candidate-loss recovery: 305 cases and malformed-proof rejection')
    check('competing intents', [Intents()], intent_steps, intent_violation)
    check('rebind intent', [Intents()], lambda s: intent_steps(s, 'rebind'),
          intent_violation, negative=True)
    activations = [Activation(saved_duress=d, duress=d) for d in (False, True)]
    check('certificate activation and recipient installation', activations,
          activation_steps, activation_violation)
    for mutant in ('clear_activation_duress', 'early_certificate', 'ack_before_key',
                   'accept_predecessor', 'recipient_rollback', 'reinstall_certificate'):
        check(mutant, activations, lambda s, m=mutant: activation_steps(s, m),
              activation_violation, negative=True)
    check('immutable capsule and bounded copying', [Capsule()], capsule_steps,
          capsule_violation)
    for mutant in ('late_compare', 'unbounded_copy'):
        check(mutant, [Capsule()], lambda s, m=mutant: capsule_steps(s, m),
              capsule_violation, negative=True)
    withdrawals = [Withdrawal(initialized=i, duty=d, acknowledged=(d == 2),
                              has_backup=b, rotation_record=r,
                              delay=(13, 7, 9) if i else (0, 0, 0))
                   for i, d, b, r in product((False, True), range(3),
                                             (False, True), (False, True))]
    withdrawals += [Withdrawal(approved=False, has_backup=b) for b in (False, True)]
    check('withdrawal lifecycle', withdrawals, withdrawal_steps, withdrawal_violation)
    for mutant in ('skip_discharge', 'reset_delay', 'abort_rollback_ack',
                   'receipt_cleanup', 'erase_fragment', 'skip_final_receipt',
                   'skip_backup_reset', 'clear_preapproval_duress'):
        check(mutant, withdrawals, lambda s, m=mutant: withdrawal_steps(s, m),
              withdrawal_violation, negative=True)
    lifecycle_checks()
    peer_ping_checks()
    binding_checks()
    cold_recovery_counterexample()
    split_lock_boundary()
    fabricated_height_boundary()
    print('Bounded protocol checks passed; cryptography and hardware remain assumptions.')


main()
```
