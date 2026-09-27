# Phone–SAR transport proposal

Status: Proposed, not adopted. Security review dated 2026-09-26.

## Objective and assessment

Phone needs a confidential channel to the selected SAR for invoice requests,
registration, and every later `DynamicRescueUpload`. It must recover from
endpoint failures without changing SAR identity or losing accepted data.

The TLS 1.3 exporter proof is a suitable basis for authenticating SAR from a
trusted `SarId`. It requires a dedicated client that binds proof verification
and subsequent requests to the same TLS connection. A certificate, DNS answer,
directory response, or successful HTTP request cannot establish SAR identity.

The existing `SarId.sar_pubkey` is sufficient as the authentication trust anchor.
The existing `SarId`, containing only that key and a Tor address, is insufficient
for independent clearnet discovery. Include bootstrap addresses in the proposed
identity below. A fresh Phone then needs no separately trusted directory,
certificate authority, certificate pin, or endpoint configuration.

This provides SAR authentication and confidential delivery of Phone requests.
`SarId` is public and cannot authenticate a Phone. SAR authorizes registration
and uploads using the application credentials described below. Neither a TLS
connection nor an upload credential proves the identity of a physical Phone
or the truth of rescue data.

## SAR identity and discovery

Proposed next-version schema:

```text
SarId {
  sar_tor_address: text,
  sar_pubkey: bytes33,
  sar_phone_bootstrap: list<text>
}
```

`sar_pubkey` remains the stable SAR identity key used by setup, receipts, and
the SAR-specific data-key derivation. `sar_phone_bootstrap` contains two to
eight distinct canonical HTTPS origins, each at most 512 ASCII bytes, served
through at least two independent ingress failure domains. At least one should
be an IP literal if loss of DNS is within the availability target. An origin
contains `https://` and a lowercase DNS A-label host or canonical IP literal;
IPv6 literals use brackets. Port 443 is implicit. Paths, explicit ports, user
information, queries, fragments, and a trailing slash are forbidden. The
transport uses fixed paths. Reject loopback, private, link-local, multicast,
and reserved destinations, including addresses obtained after DNS resolution;
bind the connection to the checked address. A local deployment profile would
need an explicit destination policy.

The complete canonical `SarId` must come through the user's trusted SAR
selection process. A key downloaded from a candidate endpoint cannot replace
it. Bootstrap entries are immutable within an existing `SarId`; endpoint
changes use a signed service record. The Tor address remains for the existing
setup and withdrawal exchanges. Phone registration and uploads have no Tor
dependency.

A public service record uses `SignedMessage` under the SAR identity key and
domain `Boomerang/sar/phone_service_record`. Its exact content tuple is:

```text
(transport_profile: u16, sar_id: SarId, generation: u64,
 not_before: u64, not_after: u64,
 endpoints: list<text>, transport_pubkeys: list<bytes33>)
```

`transport_profile` is `1`; times are UTC seconds. The endpoint list follows
the bootstrap syntax and bounds. There are one to eight distinct transport
keys. Reject duplicate entries, invalid keys, alternate encodings, unknown
profiles, and extra fields. The existing signature helper binds the locally
selected `PROTOCOL_VERSION`; retain support for registered protocol versions.
Service records and proofs must be issued for each supported version.

The record advertises routes and delegates only the Phone channel proof role
to its transport keys. Its validity interval must be positive and at most
24 hours. Phone verifies the SAR signature, complete selected `SarId`, version,
and current validity before using the delegation. It durably retains the
highest accepted generation for that `SarId` and protocol version, rejecting
lower generations or different record bytes at the same generation. Validity
requires a trustworthy Phone clock; an unauthenticated network response cannot
set it. Persist a time floor to detect clock rollback across restarts. Invalid
clock state requires recovery through the Phone's trusted time mechanism
before accepting a delegation.

Accepting a higher generation invalidates connections authenticated with an
older record before further application requests. Reconnect with the current
record. Record publication and ingress rollout must support this transition.

Records may arrive from bootstrap endpoints, mirrors, directories, or a cached
route. Sources need no identity authority. Try cached routes and bootstrap
routes independently of directory availability; unverified directory results
cannot evict them. Expired records may supply bounded routing hints, but cannot
authorize a transport key. Accept a route only after the channel proof below.
If all known routes disappear, signed discovery cannot make them reachable;
bootstrap continuity and independent mirrors remain operational requirements.

## Channel establishment

Use a dedicated native HTTP client over TLS 1.3 with ephemeral Diffie–Hellman.
The initial profile uses HTTP/1.1, full TLS handshakes, and no TLS tickets,
resumption, or early data. A future resumption profile must require ephemeral
key exchange and a fresh SAR proof on every connection. TLS cipher suites,
groups, and signature algorithms must be fixed by the adopted implementation
profile. TLS protects this channel independently of the stored-data AES
profile used by Boomlet.

Certificate chain, hostname, and certificate lifetime validation do not grant
SAR identity in this dedicated transport. Self-signed endpoint certificates
are permitted. Certificate parsing, acceptable handshake algorithms,
`CertificateVerify`, `Finished`, and all TLS integrity checks remain mandatory.
Do not implement this by weakening a shared HTTP client's verification policy.
[RFC 8446 Appendix C.5](https://www.rfc-editor.org/rfc/rfc8446.html#appendix-C.5)
allows application authentication of otherwise unauthenticated TLS; that
authentication is essential here.

The connection begins in `TLS_PROVISIONAL`. Before authentication, the only
application exchange is a bounded proof request and response. The request is
the canonical tuple `(PROTOCOL_VERSION, u16(1), phone_challenge: bytes32)`.
Phone generates a fresh challenge using SPEC Section 9.2. Send no cookies,
authorization headers, identifiers, payment data, upload keys, or uploads.

1. Both peers complete their TLS handshake and derive their own connection's
   32-byte `tls-exporter` value, using `EXPORTER-Channel-Binding` with no
   terminating NUL and a zero-length context. Use the regular exporter, never
   the early exporter. These inputs follow
   [RFC 9266 Section 2](https://www.rfc-editor.org/rfc/rfc9266.html#section-2).
2. The SAR TLS terminator chooses a currently authorized transport key and
   signs the following exact content tuple under domain
   `Boomerang/sar/phone_channel`:

   ```text
   (u16(1), sar_id: SarId, service_record_digest: bytes32,
    phone_challenge: bytes32, tls_exporter: bytes32)
   ```

   `service_record_digest` is SHA-256 of the complete canonical signed service
   record. The response is the canonical tuple of that `SignedMessage` service
   record and the `SignedMessage` channel proof. `sign_message` and canonical
   encoding have their SPEC Sections 8 and 9.3 meanings; the content is a typed
   tuple, not an extra byte-string wrapper. SAR uses its configured `SarId` and
   exporter from its own TLS session, never a client-supplied exporter.
3. Phone verifies the service record, checks that the proof signer is one of
   its authorized transport keys, and verifies the proof's signature, domain,
   version, complete selected `SarId`, record digest, outstanding challenge,
   and locally derived exporter. Only then may the connection enter
   `SAR_AUTHENTICATED` and carry invoice, registration, or upload requests.

Reject any mismatch, timeout, oversized response, or unexpected message and
close the connection. Limit the entire proof response to 16 KiB before
allocation; enforce canonical field, collection, and nesting limits as well.
The signature authenticates the TLS peer because a relay terminating two TLS
sessions has two different exporter values. The exporter is channel-binding
data, not an application encryption key.

Use one proof and one selected `SarId` per TLS connection. An exchange may
contain a bounded batch of requests under that single authentication instance.
Close at exchange completion or service-record expiry, whichever comes first.
Reject further application data after expiry. Follow
[RFC 9266 Section 4.1](https://www.rfc-editor.org/rfc/rfc9266.html#section-4.1)
for the authentication-instance boundary.

Disable automatic redirects, cookies, HTTP proxy authentication, connection
coalescing, and library retries that could send a body on another connection.
A reconnect discards proof state and repeats authentication before any body
is sent. Use fixed POST paths for protocol messages; keep identifiers out of
URLs and logs. Disable HTTP body compression and intermediary caching. Apply
SPEC size limits before accepting application bodies. Ordinary browser APIs
that cannot expose the exporter and control the connection do not satisfy
this profile.

## TLS termination and signing authority

TLS must terminate inside the trusted SAR service. A load balancer outside
that boundary must pass TLS bytes through. A terminating CDN or proxy learns
registration credentials and becomes part of SAR's security boundary, even
when it encrypts its backend connection.

The proof signer obtains the exporter directly from the terminating TLS
session. A backend exporter from a second TLS connection is different. An
HTTP header or arbitrary remote signing request carrying an exporter cannot
substitute for this association. Restrict any local signer interface to the
proof domain, configured SAR identity, valid service record, and an owned live
TLS session; it must not provide general signing authority.

Each terminator holds a separate transport private key. Keep `sar_privkey`
out of public ingress processes; protect it in SAR's controlled signing
service. Receipt and other SAR signature roles still require that identity
key under the current SPEC. A transport delegation grants none of those
roles. Pre-distribute renewed service records and replacement transport keys
with overlap, so channel establishment has no per-connection dependency on
the identity signer. The service record is an application delegation, not an
implementation of TLS delegated credentials.

Removing a transport key from a higher-generation record revokes it for Phones
that receive that record. An isolated or fresh Phone can still accept a stolen
key through a replayed, unexpired record. The 24-hour lifetime bounds that
exposure when Phone time is trustworthy. Instant revocation cannot coexist
with accepting offline records without another fresh trusted input. Test
renewal outages before fixing this lifetime for deployment. Compromise of a
trusted terminator can expose `dynamic_update_auth_key`; expiring its channel
authority does not revoke upload keys it learned.

Changing `sar_pubkey` affects the SAR-bound data key and existing setups.
Never treat root-key replacement as ordinary endpoint failover. Root
compromise or loss needs the existing fresh-setup and fund-rollover procedure,
with an independently authenticated replacement `SarId`.

## Availability and durable acceptance

Distribute ingress across providers and regions, with independent DNS and
network paths where practical. Multiple hostnames behind one ingress or one
storage service do not establish independence. Include storage, receipt
signing, service-record renewal, and payment verification in the dependency
review. Existing authenticated uploads must continue when new-registration
payment services are unavailable.

Try IPv4 and IPv6 candidates with bounded concurrency, per-stage deadlines,
and a total attempt deadline. A stalled endpoint must not prevent attempts
to other endpoints. Use fair retry rounds, exponential backoff with jitter,
and a finite backoff cap. Neither unauthenticated responses nor unbounded
`Retry-After` values may suspend all routes. Handshake and proof work need
bounded queues, cheap parsing checks, and fair admission limits; avoid a
global lockout triggered by failures naming one public identifier.

Phone durably retains each complete request before its first submission and
until the matching SAR receipt is verified. This includes the entire original
`SetupPhoneSarMessage2` after payment. Reconnect, authenticate, and retry the
same canonical bytes, IV, upload ID, and sequence number. Protect queued
registration credentials with Phone secure storage. Queue exhaustion must
report failure to persist new observations; it cannot silently evict pending
requests or claim that SAR has received them. Bound retry traffic separately
from capture and reserve service capacity for rescue processing.

Every endpoint for one `SarId` must use the same authoritative registration,
invoice and payment-consumption state, upload history, and stored receipts.
Use linearizable decisions for each identifier and upload identity, enforced
by a consensus-backed store or a fenced single writer. Eventual replication
alone permits conflicting registrations or upload bytes to be accepted at
different endpoints. Generate and durably replicate the original receipt
with the accepted record before returning it. Returning a signature before
the durable commit is not acceptance.

As a concrete availability target, three durable voting replicas in distinct
failure domains can continue with one replica unavailable, provided a majority
can communicate and the remaining signing and ingress services are reachable.
A minority partition must reject writes with `SERVICE_UNAVAILABLE`; Phone
keeps them queued. High availability cannot include successful writes in
every partition while preserving the conflict rules. An endpoint may return
a previously committed exact receipt only when it has authoritative durable
evidence of that commit.

Backups, leader election, and disaster restoration must preserve every
acknowledged upload and its exact receipt under the supported failure model.
Fence stale writers and prevent restored snapshots from accepting writes until
they have caught up. Invoice retries must recover the same payable obligation
or reconcile its payment status, rather than cause another charge. Define an
invoice request identifier and its persistence before adopting the transport.

## Registration authorization and password exposure

The channel proof authenticates SAR. For an existing identifier, SAR verifies
each upload's CMAC under the stored `dynamic_update_auth_key` before accepting
it or returning a receipt. An arbitrary TLS client has no upload authority.
Phone verifies SAR's invoice identity, protocol version, and identifier, and
verifies the original signed upload receipt before reporting success.

First registration remains vulnerable with the current SPEC derivations.
An attacker who learns an unregistered `doxing_data_identifier` can pay and
register an unrelated key and static envelope first. The first-upload CMAC
proves possession of the key supplied by that attacker; it does not bind the
key to the identifier. Keeping the identifier confidential in transit reduces
exposure but cannot repair the registration rule. Payment and rate limits
increase attack cost without establishing ownership. An invoice request alone
must never reserve an identifier irrevocably.

A concrete mitigation for the next credential version is to make the
identifier a commitment to the upload key:

```text
dynamic_update_auth_key = kdf_counter_cmac_aes256(
  doxing_key_for_sar,
  "Boomerang/sar_dynamic_update_auth_key/v2",
  canonical_encode(u16(1)),
  32
)
doxing_data_identifier = tagged_sha256(
  "Boomerang/doxing_data_identifier/v2",
  dynamic_update_auth_key
)
```

Here `u16(1)` is a fixed credential-profile context. The key derivation is
independent of the identifier, avoiding a circular definition. The key and
identifier are stable across message-version changes; upload authentication
still binds the registered `PROTOCOL_VERSION`. Before taking ownership or
committing registration, SAR recomputes the identifier from the supplied key
and compares it in constant time. Existing invoice, payment, first-upload,
conflict, and atomic-commit checks also apply. Learning the identifier alone
then does not enable an unrelated-key registration. SAR receives no rescue
decryption key.

This requires coordinated changes to Phone, Boomlet's identifier derivation,
duress lookup, replacement-Phone recovery, and versioned conformance vectors.
It is a credential migration, not a transport-only change; existing registered
identifiers cannot be rewritten in place. Adoption must choose this mitigation
or explicitly retain the first-registration risk. Proving ownership cannot
stop a password holder from registering fabricated data.

Both the current identifier and the proposed commitment permit offline
password testing: a guess deterministically yields the SAR-specific key and
identifier. No ciphertext or upload-key leak is needed once the identifier is
known. Use a generated doxing secret with at least 128 bits of entropy. A
human-chosen low-entropy password remains vulnerable, including to SAR itself.
A slower password KDF would need a separate design compatible with Boomlet;
transport changes cannot supply missing entropy. Retained upload keys also
let compromised or retired Phones append indefinitely under the existing
credential lifecycle.

## Security gaps and disposition

| Gap | Mitigation in this proposal | Remaining exposure |
| --- | --- | --- |
| Endpoint substitution or two-session proof relay | Verify a SAR-authorized signature over the locally derived TLS exporter and exact identity before any sensitive request | A substituted initial `SarId` defeats authentication; trusted selection remains necessary |
| Directory outage, poisoned routes, or discovery rollback | Bootstrap routes in `SarId`, independent route sources, destination checks, signed records, cached generation | All routes can be blocked; a fresh Phone can receive an older record within its validity interval |
| Root key spread across ingress nodes | Separate transport keys with narrowly scoped, expiring SAR authorization | Trusted terminators see credentials; root compromise and credential theft need separate recovery |
| Proxy termination or accidental request replay before proof | Exporter at the real TLS terminator, dedicated connection state, bounded parsing, manual authenticated retries | Requires evidence from the actual Phone and ingress stacks |
| Split-brain acceptance or lost acknowledged writes | Quorum commit, fencing, durable original receipts, exact retries | Minority partitions and failures beyond the storage target reduce availability |
| Identifier squatting | Proposed upload-key commitment plus registration preimage check | Requires a credential-version change; current SPEC remains exposed |
| Offline password guessing | Generated high-entropy doxing secret | Existing weak passwords and compromised Phones remain exposed |
| Denial of service and storage exhaustion | Bounded admission, fair failover, persistent queues, explicit capacity failures | Infinite retention and unlimited outage buffering are impossible; capacity and retention policy still need deployment evidence |
| Clearnet correlation | Minimize headers and logs; keep retry and acknowledgment behavior independent of duress | SAR IPs, DNS, SNI, timing, sizes, payments, and IP-based denial remain observable |

## Adoption and verification

Keep this proposal separate from the adopted SPEC until the schema and
credential choices are approved. Adoption must update SPEC Sections 8–10,
13.1, 19.4, and 20; the wire catalog; setup flows and guards; and the relevant
security-model assumptions. Adding `sar_phone_bootstrap` changes canonical
`SarId` bytes and every signed context containing them. Allocate a new schema
version and provide migration rules; do not append a field to existing
canonical objects silently. The proposed numeric bounds and record lifetime
need boundary and outage evidence before production use.

Required evidence:

- A Phone supplied only the proposed trusted `SarId` discovers and authenticates
  a self-signed endpoint. A CA-valid attacker endpoint cannot pass the proof.
  Cover direct and pass-through ingress, and reject proof relay through two
  independently terminated TLS sessions or a client-supplied exporter.
- Reject wrong SAR, record signer, delegated signer, domain, version, record
  digest, challenge, exporter, field type, or encoding. Exercise record expiry,
  rollback, conflicting generations, clock rollback, and the bounded stale
  record accepted by a fresh Phone. A transport key cannot sign an accepted
  root-role receipt.
- Instrument the actual client to show zero sensitive bytes before proof,
  including headers, redirects, reconnects, library retries, and parallel
  requests. Cover invalid TLS handshakes, TLS downgrade, early data, and
  unsupported exporter APIs.
- Remove one ingress and one storage replica within the declared failure
  model; test DNS failure, stalled endpoints, service-record renewal outages,
  invalid-route floods, and exhausted queues. Record time to a verified receipt.
- Partition the store, race conflicting registrations and uploads at different
  endpoints, crash around commit, lose replies, and restore stale backups.
  Verify one accepted value, durable original receipts, and exact retry bytes.
  Test paid-registration recovery without duplicate charges.
- Reproduce the leaked-identifier first-registration attack under the current
  derivation. For the proposed credential version, reject unrelated keys and
  verify consistent identifier derivation in Phone, Boomlet, and rescue lookup.
  Demonstrate that weak-password guesses remain testable offline.

Focused experiments run on 2026-09-26 passed all 19 checks using in-memory
OpenSSL TLS 1.3 sessions and the existing
test-only cryptographic helpers. They establish matching exporters at the two
ends of one session, rejection of a proof relayed across two sessions, and
signature binding to the identity, challenge, record, domain, and version.
They also demonstrate that a signer accepting an arbitrary caller-supplied
exporter would admit that relay.

The existing bounded registration model reproduced unrelated-key registration
under a leaked identifier and subsequent rejection of the legitimate key.
Payment and static-data handling are outside that model; the attack assumes
the attacker can pay. The proposed commitment accepts its matching key and
rejects an unrelated key. Dictionary trials confirmed offline guessing from
either identifier derivation alone.

These experiments do not validate HTTP request gating, canonical parsing,
service-record lifecycle, discovery, actual Phone APIs, payment recovery, or
distributed storage. Those adoption tests remain pending.
