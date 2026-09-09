#!/usr/bin/env python3
"""Bounded executable checks for the decision rules in wt_failover/README.md.

Safety: one honest peer plus four adversarial cosigners. Any honest PREPARE or
COMMIT can be completed into a five-signature certificate by the adversary,
including while that certificate remains hidden. Enumerate three ballots and
all certificate deliveries/recovery selections, preserving the honest journal.

Recovery: five honest peers, all initial prepare/learn/commit/install subsets,
candidate loss, exact journal restoration, and delayed old prepared proofs.
This is an authenticated decision abstraction, not a crypto/network or full
withdrawal implementation. Crashes preserve durable state; rollback is excluded.
"""

from collections import deque
from copy import deepcopy
from dataclasses import dataclass, replace


ACTIVATE, ABORT = 0, 1
NAMES = ("ACTIVATE", "ABORT")
PEERS = tuple(range(5))
NONE, UNISSUED = -1, -2
BALLOTS = 3


@dataclass(frozen=True)
class SafetyState:
    ballot: int = 0
    prepared: tuple = (NONE,) * BALLOTS
    highest: int = NONE  # certificate encoded as 2 * ballot + value
    reports: tuple = (UNISSUED,) * BALLOTS
    committed: tuple = (NONE,) * BALLOTS


def at(values, index, value):
    return values[:index] + (value,) + values[index + 1:]


def safety_steps(state, mutant=None):
    """All choices four Byzantine cosigners can justify to the honest peer."""
    b = state.ballot
    possible = {
        2 * old + value
        for old, value in enumerate(state.prepared)
        if value != NONE
    }
    if state.prepared[b] == NONE:
        if b == 0:
            values = {ACTIVATE}
        else:
            own = state.reports[b]
            assert own != UNISSUED
            # Four reports may omit proofs or carry any actually possible older
            # proof, but the fifth must be the honest peer's exact signed report.
            maxima = {own} | {qc for qc in possible if own <= qc < 2 * b}
            values = {ABORT if qc == NONE else qc % 2 for qc in maxima}
        for value in sorted(values):
            yield f"prepare {b} {NAMES[value]}", replace(
                state, prepared=at(state.prepared, b, value)
            )
    if state.prepared[b] != NONE:
        qc = 2 * b + state.prepared[b]
        if state.highest != qc:
            yield f"retain prepared certificate {b}", replace(state, highest=qc)
        if state.highest == qc and state.committed[b] == NONE:
            yield f"commit {b} {NAMES[qc % 2]}", replace(
                state, committed=at(state.committed, b, qc % 2)
            )
    for target in range(b + 1, BALLOTS):
        reported = NONE if mutant == "omit_highest" else state.highest
        yield f"promise/report ballot {target}", replace(
            state,
            ballot=target,
            reports=at(state.reports, target, reported),
        )
    if mutant == "allow_old_commit":
        for qc in sorted(possible):
            old, value = divmod(qc, 2)
            if old < b and state.committed[old] == NONE:
                yield f"BUG: late commit {old} {NAMES[value]}", replace(
                    state,
                    highest=max(state.highest, qc),
                    committed=at(state.committed, old, value),
                )


def safety_search(mutant=None):
    initial = SafetyState()
    queue = deque([initial])
    parent = {initial: None}
    edges = 0
    while queue:
        state = queue.popleft()
        # Four Byzantine cosigners can complete every honest COMMIT, whether or
        # not the honest peer receives that final certificate. Two values here
        # therefore witness two potentially valid conflicting final certificates.
        if len(set(state.committed) - {NONE}) > 1:
            trace = []
            cursor = state
            while parent[cursor] is not None:
                cursor, action = parent[cursor]
                trace.append(action)
            return len(parent), edges, list(reversed(trace))
        for action, successor in safety_steps(state, mutant):
            edges += 1
            if successor not in parent:
                parent[successor] = state, action
                queue.append(successor)
    return len(parent), edges, None


@dataclass(frozen=True)
class Certificate:
    stage: str
    ballot: int
    value: int
    signers: tuple = PEERS


@dataclass(frozen=True)
class Report:
    signer: int
    target: int
    highest: Certificate | None


class Rejected(Exception):
    pass


def require(condition):
    if not condition:
        raise Rejected()


class Peer:
    def __init__(self, identity, ready):
        self.identity = identity
        self.ready = ready  # retained original local prerequisites
        self.ballot = 0
        self.prepared = {}
        self.highest = None
        self.reports = {}
        self.committed = {}
        self.decided = None

    def restore(self):
        # Every field here is durable. Restoring excludes any external proof
        # buffer; subsequent COMMIT must work from the retained certificate.
        restored = Peer(self.identity, self.ready)
        for field in ("ballot", "prepared", "highest", "reports", "committed", "decided"):
            setattr(restored, field, deepcopy(getattr(self, field)))
        return restored

    def recover(self, target):
        require(self.decided is None)
        if target in self.reports:
            require(target == self.ballot)
            return self.reports[target]
        require(target > self.ballot)
        self.ballot = target
        report = Report(self.identity, target, self.highest)
        self.reports[target] = report
        return report

    def prepare(self, value, peers, reports=None, candidate_available=False):
        require(self.decided is None)
        if self.ballot == 0:
            require(value == ACTIVATE and self.ready and candidate_available)
        else:
            require(reports is not None)
            require(tuple(report.signer for report in reports) == PEERS)
            require(all(report.target == self.ballot for report in reports))
            require(reports[self.identity] == self.reports[self.ballot])
            certificates = [report.highest for report in reports if report.highest]
            for qc in certificates:
                verify(qc, "prepare", peers)
                require(qc.ballot < self.ballot)
            if certificates:
                highest_ballot = max(qc.ballot for qc in certificates)
                values = {qc.value for qc in certificates if qc.ballot == highest_ballot}
                require(len(values) == 1 and value in values)
            else:
                require(value == ABORT)
            if value == ACTIVATE:
                # A real activation proof contains this peer's prior PREPARE;
                # never recheck live candidate/SAR availability during recovery.
                require(self.ready)
        previous = self.prepared.get(self.ballot, value)
        require(previous == value)
        self.prepared[self.ballot] = value
        return ("prepare", self.identity, self.ballot, value)

    def retain(self, certificate, peers):
        verify(certificate, "prepare", peers)
        require(self.decided is None and certificate.ballot == self.ballot)
        require(self.prepared.get(self.ballot) == certificate.value)
        self.highest = certificate

    def commit(self, ballot):
        require(self.decided is None and ballot == self.ballot)
        require(self.highest is not None and self.highest.ballot == ballot)
        value = self.highest.value
        require(self.prepared.get(ballot) == value)
        require(self.committed.get(ballot, value) == value)
        self.committed[ballot] = value
        return ("commit", self.identity, ballot, value)

    def install(self, certificate, peers):
        verify(certificate, "commit", peers)
        require(self.decided is None or self.decided.value == certificate.value)
        # The certificate may be older than the promise. It is already decided.
        self.decided = certificate


def verify(certificate, stage, peers):
    require(certificate.stage == stage and certificate.signers == PEERS)
    for peer in peers:
        votes = peer.prepared if stage == "prepare" else peer.committed
        require(votes.get(certificate.ballot) == certificate.value)


def reject(call):
    try:
        call()
    except Rejected:
        return
    raise AssertionError("Invalid transition was accepted")


def subsets(mask):
    value = mask
    while True:
        yield value
        if value == 0:
            break
        value = (value - 1) & mask


def recovery_cases():
    count = 0
    full = (1 << len(PEERS)) - 1
    for prepared_mask in range(full + 1):
        learned_masks = range(full + 1) if prepared_mask == full else (0,)
        for learned_mask in learned_masks:
            for committed_mask in subsets(learned_mask):
                installed_masks = range(full + 1) if committed_mask == full else (0,)
                for installed_mask in installed_masks:
                    peers = [Peer(i, bool(prepared_mask & (1 << i))) for i in PEERS]
                    for peer in peers:
                        if peer.ready:
                            peer.prepare(ACTIVATE, peers, candidate_available=True)
                    old_prepared = Certificate("prepare", 0, ACTIVATE)
                    old_final = Certificate("commit", 0, ACTIVATE)
                    for peer in peers:
                        if learned_mask & (1 << peer.identity):
                            peer.retain(old_prepared, peers)
                    peers = [peer.restore() for peer in peers]
                    for peer in peers:
                        if committed_mask & (1 << peer.identity):
                            peer.commit(0)
                    for peer in peers:
                        if installed_mask & (1 << peer.identity):
                            peer.install(old_final, peers)
                    peers = [peer.restore() for peer in peers]
                    if installed_mask:
                        # A decided peer returns the final certificate rather
                        # than blocking recovery by withholding a new report.
                        for peer in peers:
                            peer.install(old_final, peers)
                    else:
                        reports = tuple(peer.recover(1) for peer in peers)
                        peers = [peer.restore() for peer in peers]
                        assert tuple(peer.recover(1) for peer in peers) == reports
                        target = ACTIVATE if learned_mask else ABORT
                        for peer in peers:
                            # Reject late old prepared proofs/COMMIT after the
                            # higher promise, including a hidden complete proof.
                            reject(lambda peer=peer: peer.retain(old_prepared, peers))
                            reject(lambda peer=peer: peer.commit(0))
                            peer.prepare(target, peers, reports)
                        current_prepared = Certificate("prepare", 1, target)
                        for peer in peers:
                            peer.retain(current_prepared, peers)
                        peers = [peer.restore() for peer in peers]
                        for peer in peers:
                            peer.commit(1)
                        current_final = Certificate("commit", 1, target)
                        # Final certificates remain learnable under a still
                        # higher promise, with candidate availability false.
                        for peer in peers:
                            peer.recover(2)
                            peer.install(current_final, peers)
                    assert len({peer.decided.value for peer in peers}) == 1
                    if committed_mask == full:
                        assert all(peer.decided.value == ACTIVATE for peer in peers)
                    count += 1
    return count


def rejection_cases():
    peers = [Peer(i, True) for i in PEERS]
    for peer in peers:
        peer.prepare(ACTIVATE, peers, candidate_available=True)
    qc = Certificate("prepare", 0, ACTIVATE)
    for malformed in (
        replace(qc, signers=(0, 1, 2, 3)),
        replace(qc, signers=(0, 1, 2, 3, 3)),
        replace(qc, signers=(1, 0, 2, 3, 4)),
        replace(qc, value=ABORT),
        replace(qc, ballot=1),
        replace(qc, stage="commit"),
    ):
        reject(lambda: peers[0].retain(malformed, peers))
    peers[0].retain(qc, peers)
    reports = tuple(peer.recover(1) for peer in peers)
    reject(lambda: peers[0].prepare(ABORT, peers, reports))
    reject(lambda: peers[0].prepare(ACTIVATE, peers, reports[:-1]))
    swapped = (reports[1], reports[0], *reports[2:])
    reject(lambda: peers[0].prepare(ACTIVATE, peers, swapped))
    omitted_own = (replace(reports[0], highest=None), *reports[1:])
    reject(lambda: peers[0].prepare(ABORT, peers, omitted_own))


def main():
    states, edges, conflict = safety_search()
    assert conflict is None, conflict
    print(f"Safety: {states} states, {edges} transitions, {BALLOTS} ballots; no conflicting final certificates.")
    for mutant in ("omit_highest", "allow_old_commit"):
        _, _, counterexample = safety_search(mutant)
        assert counterexample, f"Negative control did not fail: {mutant}"
        print(f"Negative control {mutant}: conflicting certificates detected.")
        print("  " + " -> ".join(counterexample))
    count = recovery_cases()
    assert count == 305
    print(f"Recovery: all {count} five-peer prepare/learn/commit/install cases complete with the candidate absent.")
    rejection_cases()
    print("Malformed proofs, wrong recovery choices, own-report substitution, and stale COMMIT are rejected.")
    print("Bounded authenticated decision model only; not full protocol verification or unbounded liveness.")


if __name__ == "__main__":
    main()
