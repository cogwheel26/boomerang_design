# Coercion Economics

**Document status:** Non-normative rationale.

`spec/SPEC.md` defines protocol behavior. `security_models/README.md` contains
the active threat model and risk register. This note preserves the economic
deterrence argument that motivated Boomerang's timing and duress design.

## Economics Of Coercion

Boomerang is designed not only to function under coercion, but also to be a
deterrent by increasing attacker uncertainty and cost.

### A Simple Game-Theoretic Model

Model a coercion attempt as a sequential decision problem:

**Players**

- Defender: Boomerang user or users
- Attacker: coercive adversary

**Parameters**

- `V`: value attacker can steal
- `T`: time attacker must maintain control until funds are safely exfiltrated
- `c`: attacker's per-unit-time operational cost
- `q(T)`: probability attacker is disrupted before completion, increasing with
  time
- `L`: attacker loss if disrupted

A simple attacker expected utility:

```text
U_A = (1 - q(T)) * V - c * T - q(T) * L
```

The attacker proceeds when `U_A > 0`.

### How Boomerang Shifts Incentives

Boomerang changes the attacker's payoff by changing the distribution of `T`
and increasing `q(T)`:

- It increases expected completion time because Boomlet will not sign until its
  secret mystery threshold is reached.
- It increases variance because the attacker must plan for worst-case duration.
- It reduces time compressibility because the victim cannot force Boomlet to
  sign early.
- It creates a reaction window because duress checks happen at commitment and
  recur during the digging game.

The objective is not coercion-proof custody. The objective is to push attacker
expected utility negative for a meaningful range of attackers by raising time,
uncertainty, and disruption probability.

### Parameter Knobs As Economic Levers

Several design parameters are deterrence levers:

- Mystery min/max range affects expected duration and variance.
- Duress check interval affects duress opportunities and ceremony burden.
- Milestone schedule defines when deterministic fallback becomes available.
- WT redundancy and censorship resistance affect whether an attacker can force
  fallback behavior.
- SAR selection and jurisdiction affect the real-world meaning of `q(T)`.

## Realistic Cost Assumptions

Boomerang's coercion-resistance argument is based on altering the economics of
coercion, not on making coercion impossible.

To evaluate deterrence, examine:

1. The realistic cost of sustaining coercion.
2. The statistical duration of withdrawal under Boomerang.
3. The probability and consequence of SAR escalation.
4. The rational behavior of an attacker facing uncertainty.

### Expected Withdrawal Duration

In a typical high-security configuration:

- 5 peers
- Withdrawal window: 6-9 months
- Each peer samples a hidden threshold independently

Because completion depends on the maximum of all peers' hidden values, the
effective withdrawal duration clusters near the upper bound. For an attacker,
coercion must likely be sustained for close to the full configured window.

### Sustained Coercion Cost

A coercive detention lasting months requires continuous staffing, secure
holding locations, logistics, surveillance countermeasures, and operational risk
management.

Conservative estimates:

- Low-end aggressive underestimation: about USD 5,000 per day
- Professional sustained operation: about USD 20,000-30,000 per day

Over a 6-9 month window, even the low estimate implies about USD 900,000 to
USD 1,350,000 in coercion cost before escalation risk. Professional costs can
reach several million dollars.

### Escalation Probability

If duress checks occur weekly, the victim successfully signals with probability
`pi` per check, and SAR responds with probability `rho` after a signal, then
over a 6-9 month period the probability of at least one escalation can become
very high unless `pi` or `rho` is near zero.

The relevant question is then what escalation means for the attacker.

### Two Escalation Regimes

If SAR activation plausibly leads to detention, prosecution, asset seizure, or
severe criminal penalties, escalation represents catastrophic loss. Under those
conditions, expected attacker loss can dominate potential gain, and the
attacker's rational strategy can become abandonment.

If SAR activation does not meaningfully disrupt the operation, create
prosecution risk, or impose material cost, escalation is only a nuisance. In
that regime, Boomerang provides delay and detection, but deterrence is weaker
for very large target values.

### Attacker Decision Dynamics

Boomerang turns coercion into a sequential decision problem. Each passing week
without completion suggests a high hidden threshold, leaves substantial
expected remaining time, and increases the probability that escalation has
already occurred.

Under strong escalation consequences, the attacker's expected payoff declines
toward early abandonment. Under weak escalation consequences, the attacker may
rationally continue.

### Practical Implication

Boomerang is strongest when:

- legal enforcement is credible;
- SAR capability is real;
- duress signaling reliability is high;
- the withdrawal window is long relative to target value.

Boomerang is weaker when:

- escalation has no real consequence;
- jurisdictional enforcement is absent;
- duress signaling is unreliable.

The core point is economic: delay alone does not deter coercion. Delay combined
with credible escalation can.
