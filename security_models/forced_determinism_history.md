# Forced-determinism design discussion

> **Last change — 2026-07-14:** ADR 0006 places `mystery` generation at `DIGGING` entry rather than setup.

## Discussion

### Comment 1

As things stand, peers must renew a funded Boomerang setup before it becomes
deterministic. That is both a usability problem and the second
forced-determinism attack vector. An Ajolote-like mechanism might remove the
need for renewal when no withdrawal has started:

```text
user UTXO
  -- setup transaction --> Boomerang vaulted UTXO
  -- withdrawal transaction --> Boomerang unvaulted UTXO
  -- nondeterministic transaction using Boomlet keys, or relatively timelocked
     deterministic transaction using normal keys --> Boomerang spend UTXO
```

The drawback is that there would no longer be a single static Boomerang
address. Every deposit would need a fresh set of Boomerang transactions. That
makes Boomerang much less useful as an Ajolote fallback. We could partly work
around this by marking the setup transaction `ANYONECANPAY` and preparing it
for a fixed output, say 1 BTC. The address would then be a fixed-capacity
Boomerang store that could serve as an Ajolote fallback.

This mechanism does not address determinism attacks during withdrawal, such as
an attacker breaking a peer's Boomlet.

### Comment 2

A deleted-key construction might look like this:

1. Create a descriptor whose Boom leaf is constant. Normal leaves can remain
   derived from a master normal key. Generate the vault leaf when disposing of
   the enforcement key.
2. Use a gate address to avoid relying on outsiders and retain more control.
3. Place the vault leaf high in the tree so it does not affect the inclusion
   proofs of lower leaves.
4. Generate a new address for each disposal because the enforcement keys to be
   deleted must be regenerated.
5. During withdrawal, Boomlet must sign a different inclusion proof for each
   address. Boomlet must therefore understand the control blocks or trust
   another entity to provide them.

I think those details can be solved one way or another. The harder part is that
the unvault transaction has to pay to another Boomerang address. That leaves
four questions:

1. What happens if an adversary obtains the presigned transactions?
2. Who is trusted to hold them?
3. How much nesting is suitable?
4. What happens to the last Boomerang?

My intuition is that this will not work as intended.

### Comment 3

We should not let Boomlet accelerate its counter near the end of the Boomerang
period. That would let an attacker lie about the current block height and push
Boomlet into signing too early.

### Comment 4

What are we trying to prevent, and why? An external party should not be able to
force us to wait until the normal period begins. There are two reasons:

1. An adversary may have compromised the normal keys and be waiting for them to
   become usable.
2. Other peers may wait for the normal period so they can move the funds without
   one user's consent.

### Comment 5

What if we remove the normal period altogether? The problem then becomes how to
back up Boomlet without undermining its purpose as an enforcement device. Even
if we solve that, digital media is still vulnerable to events such as EMP.
Relying on digital data alone would be risky.

### Comment 6

An attestation service introduces a liveness problem. An attacker could deny
service to the attestation server and prevent a timely response when the
reaction window is short.

### Comment 7

The case against relying only on digital data is:

1. Digital data can be deleted.
2. Bit rot or device failure can make it irretrievable.
3. It separates users from Bitcoin's base-layer recovery model. This is why
   Lightning is not used for significant sums and why Ajolote and deleted-key
   covenants are not used. A cold-storage protocol should retain a basic path
   grounded in Bitcoin's base-layer security.

### Comment 8

A cryptographic puzzle might help here. I am not sure a card has enough
processing power for a useful one, though. With a sequential,
non-parallelizable puzzle, the card could export a backup that takes roughly
`mystery` blocks to recover. The backup could hold the Boom key or, after
changes to the withdrawal procedure, the withdrawal transaction.

### Comment 9

More detail on attestation: it could show that the server's secure element runs
the approved code and generated its public key internally. We could include
that key in the spending conditions and allow it to sign only transactions that
move funds from one Boomerang setup to another with the same participant keys.
Maybe Boomlet could enforce the same rule if it can inspect the outputs.

### Comment 10

This still seems unworkable. How would the attestation service know in advance
which Boomlet key will be generated? If the idea is to use exactly the same
keys, then we are reusing them. Boomlet also has to know about the rollover path
and its rules; otherwise, the UTXO could be unspendable during the Boomerang
period.
