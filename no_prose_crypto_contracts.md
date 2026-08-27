# No-prose cryptographic notation

The no-prose sequence diagrams use the following calls as exact abbreviations.
Arguments are evaluated exactly as written at the call site.

## Entity material

| Entity | `private(E)` | `public(E)` | `name(E)` |
| --- | --- | --- | --- |
| `Boomlet_i` | `boomlet_i_identity_privkey` | `boomlet_i_identity_pubkey` | `"boomlet"` |
| `ST_i` | `st_i_identity_privkey` | `st_i_identity_pubkey` | `"st"` |
| `WT` | `wt_privkey` | `wt_pubkey` | `"wt"` |
| `SAR` | `sar_privkey` | `sar_pubkey` | `"sar"` |
| `Boomletwo` | `boomletwo_Identity_privkey` | `boomletwo_Identity_pubkey` | `"boomletwo"` |

`Boomlet_i` also covers a public key read as
`peer_ids_collection[i].boomlet_identity_pubkey`. A concrete suffix such as
`Boomlet_0` or `ST_1` selects that concrete peer's material.

## Channel operations

`C-SEAL(S, R, context, content)` expands to:

```text
cbc_cmac_encrypt(
  keys: channel_keys(
    private(S), name(S), public(R), name(R),
    sender_public_key: public(S),
    receiver_public_key: public(R)),
  context: context,
  content: content)
```

`C-OPEN(R, S, context, envelope)` expands to:

```text
cbc_cmac_decrypt(
  keys: channel_keys(
    private(R), name(R), public(S), name(S),
    sender_public_key: public(S),
    receiver_public_key: public(R)),
  context: context,
  envelope: envelope)
```

The argument order records the direction. `C-SEAL` lists sender then receiver;
`C-OPEN` lists receiver then sender.

## SAR stored-data operations

`C-SAR-STORE-SEAL(key, context, content)` expands to:

```text
cbc_cmac_encrypt(
  keys: derive_cbc_cmac_keys(key, "Boomerang/sar_stored_data"),
  context: context,
  content: content)
```

`C-SAR-STORE-SEAL(key, context, content, iv)` adds the supplied `iv` argument
to that exact call.

`C-SAR-STORE-OPEN(key, context, envelope)` expands to:

```text
cbc_cmac_decrypt(
  keys: derive_cbc_cmac_keys(key, "Boomerang/sar_stored_data"),
  context: context,
  envelope: envelope)
```
