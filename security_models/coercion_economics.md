# Coercion Economics

> **Last change — 2026-07-14:** Deterrence applies to rational, cost-sensitive attackers and depends on credible disruption outside the protocol.

Boomerang's coercion claim is economic rather than absolute. A long,
unpredictable withdrawal raises the cost of an attack, and the victim cannot
shorten the wait on the attacker's behalf.

### Attacker utility model

Model a coercion attempt as a sequential decision problem:

**Players:**

- Defender: Boomerang user or users
- Attacker: coercive adversary

**Parameters:**

- `V`: value attacker can steal
- `T`: time attacker must maintain control until funds are safely exfiltrated
- `c`: attacker's per-unit-time operational cost
- `q(T)`: assumed probability that an external actor disrupts the attacker
  before completion; it increases with time only when detection and response
  make that assumption credible
- `L`: attacker loss if disrupted

The attacker's expected utility is:

```text
U_A = (1 - q(T)) * V - c * T - q(T) * L
```

The attacker proceeds when `U_A > 0`.

The equation covers a rational, cost-sensitive attacker seeking financial gain.
It does not cover retaliatory, ideological, state, or self-destructive actors,
or an attacker who assigns positive utility to harming the victim. The `c * T`
term charges cost through completion. If disruption ends the attack at an
earlier time `D`, incurred cost is closer to `c * min(T, D)`; that stopping-time
behavior is outside this simplified equation.

### How Boomerang changes the incentives

Boomerang changes the distribution of `T`. It raises `q(T)` only if signaling,
investigation, or intervention outside the protocol becomes more likely over
time:

- Each Boomlet samples a fresh secret threshold when the approved withdrawal
  enters `DIGGING` and will not sign before reaching it, which lengthens the
  expected attack.
- The attacker has to plan for the upper end of the range, not just its mean.
- The victim cannot force an early signature.
- Duress checks at commitment and during the digging game create repeated
  opportunities to signal. Fixed-deadline acknowledgements confirm protocol
  delivery without proving that the external response is timely, effective,
  lawful, correctly directed, or safe.

Boomerang does not make custody coercion-proof. It aims to make expected utility
negative for a meaningful range of attackers by increasing the required time,
uncertainty, and probability of disruption.

### Protocol parameters as economic levers

Deterrence depends on:

- Mystery min/max range affects expected duration and variance.
- Duress check interval affects duress opportunities and ceremony burden.
- Milestone schedule defines when deterministic fallback becomes available.
- WT redundancy and censorship resistance affect whether an attacker can force
  fallback behavior.
- SAR selection and jurisdiction affect the real-world meaning of `q(T)`.

## Cost assumptions

Boomerang's coercion-resistance argument is based on altering the economics of
coercion, not on making coercion impossible.

The argument depends on four estimates:

1. The realistic cost of sustaining coercion.
2. The statistical duration of withdrawal under Boomerang.
3. The probability and consequence of SAR escalation.
4. The rational behavior of an attacker facing uncertainty.

### Expected withdrawal duration

Example high-security configuration:

- 5 peers
- Withdrawal window: 6-9 months
- Each peer samples a hidden threshold independently

Because completion depends on the maximum of all peers' hidden values, the
effective withdrawal duration clusters near the upper bound. For an attacker,
coercion must likely be sustained for close to the full configured window.

### Cost of sustained coercion

A coercive detention lasting months requires continuous staffing, secure
holding locations, logistics, surveillance countermeasures, and operational risk
management.

Illustrative estimates:

- Low-end aggressive underestimation: about USD 5,000 per day
- Professional sustained operation: about USD 20,000-30,000 per day

These figures have no cited jurisdiction, date, source distribution, or
sensitivity range. They are examples, not evidence for a security claim.

Over a 6-9 month window, even the low estimate implies about USD 900,000 to
USD 1,350,000 in coercion cost before escalation risk. Professional costs can
reach several million dollars.

### Escalation probability

If duress checks occur weekly, the victim successfully signals with probability
`pi` per check, and SAR responds with probability `rho` after a signal, then
over a 6-9 month period the probability of at least one escalation can become
very high unless `pi` or `rho` is near zero.

The effect depends on what escalation means for the attacker.

### Two escalation regimes

If SAR activation plausibly leads to detention, prosecution, asset seizure, or
severe criminal penalties, escalation represents catastrophic loss. Under those
conditions, expected attacker loss can dominate potential gain, and the
attacker's rational strategy can become abandonment.

If SAR activation does not meaningfully disrupt the operation, create
prosecution risk, or impose material cost, escalation is only a nuisance. In
that regime, Boomerang provides delay and detection, but deterrence is weaker
for very large target values.

### Attacker decisions over time

Boomerang turns coercion into a sequential decision problem. Each passing week
without completion suggests a high hidden threshold, leaves substantial
expected remaining time, and increases the probability that escalation has
already occurred.

Under strong escalation consequences, the attacker's expected payoff declines
toward early abandonment. Under weak escalation consequences, the attacker may
rationally continue.

### Practical implication

The deterrent depends on credible enforcement, a SAR that can actually respond,
reliable duress signaling, and a withdrawal window long enough for the value at
stake. If escalation has no real consequence, jurisdictional enforcement is
absent, or duress delivery is unreliable, Boomerang mainly buys time. Delay by
itself does not deter coercion; delay backed by credible escalation can.
