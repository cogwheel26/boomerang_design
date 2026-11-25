# Self-contained ping checks

These finite checks evaluate the DIGGING threshold policies in
[the proposal](boomlet_rollover.md). They assume a valid authenticated checkpoint
for one withdrawal and one common unit of valid counter progress. They do not
establish real elapsed block time, latest-state recovery or activation
implementation conformance.

Run from the repository root. No files are created or diagrams rendered.

```sh
python3 -B - <<'PY'
from pathlib import Path
s = Path('wip and stale/proposals/wt_failover/boomlet_rollover_model.md').read_text()
exec(compile(s.split('```python\n', 1)[1].split('\n```', 1)[0],
             'wip and stale/proposals/wt_failover/boomlet_rollover_model.md', 'exec'))
PY
```

```python
checked = 0
for upper in range(1, 21):
    for lower in range(1, upper + 1):
        for original in range(lower, upper + 1):
            for saved_counter in range(original):
                for actual_counter in range(saved_counter, original):
                    old_remaining = original - actual_counter
                    for redraw in range(lower, upper + 1):
                        floor_remaining = max(original, redraw) - saved_counter
                        independent_remaining = upper + redraw - saved_counter
                        assert floor_remaining >= old_remaining
                        assert independent_remaining >= old_remaining
                        checked += 1
print(f'PASS {checked} threshold cases, including conservatively stale counters')

# Restoring earned counter credit against a fresh raw threshold can make an
# unreached withdrawal finish without any further valid progress.
raw_immediate = sum(redraw <= 80 for redraw in range(1, 101))
assert raw_immediate == 80
print('NEGATIVE raw redraw with counter 80: 80/100 draws finish immediately')

# A complete signed packet can be exactly the same observation in distinct
# valid source histories. All four other peers may return identical stale
# packets and identical authenticated but dishonest completeness claims.
checkpoint = ('setup', 'withdrawal', 'head0', 12, 'safe duty discharged', 'no vote')
observations = (checkpoint, ('peer1 latest', 'peer2 latest',
                              'peer3 latest', 'peer4 latest'))
histories = [
    (observations, 'source lost at checkpoint', ()),
    (observations, 'source lost after checkpoint', ('undelivered duress duty',)),
    (observations, 'source lost after checkpoint', ('hidden ACTIVATE COMMIT',)),
    (observations, 'source lost after checkpoint', ('later consent rotation',)),
]
assert all(h[0] == observations for h in histories)
assert len({h[2] for h in histories}) == 4
print('BOUNDARY one packet observation fits four different security histories')

# Exact checkpoint progress is not equivalent to ping sequence. Each valid
# no-advance pong can produce another ping without increasing the counter.
ping_sequence = 12
counter = 3
for _ in range(5):
    ping_sequence += 1
assert ping_sequence == 17 and counter == 3
print('BOUNDARY five additional pings need not add any counter progress')
```

The threshold search covers positive uniform supports with upper bound at most
20, every unreached original draw, saved counter, possible later unreached
counter and independent replacement draw. The algebraic inequalities in the
proposal establish the same bound beyond this finite range, assuming a common
progress unit and an authentic counter. The four histories illustrate missing
information; they are not a model of a complete recovery protocol.
