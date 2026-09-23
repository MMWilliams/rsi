# Library change: source/library/193/g6

Run: `library-inheritance-20260916-v7`. Semantic audit: **passed**.

This explanation reads recorded evidence; it performs no new search and does not establish a causal mechanism.

## Parent and proposal rule

Mode: `library`. Parent stored library entries: 13 (the historical four-atom entry is ignored by search).
Parent development score: 10/16; admission score: 12/16.

Library candidates rank by visible compatibility, number of supporting solution certificates, fragment length, then lexical text. Numeric and frozen controls use their declared fixed proposals.
This generation added 15 fragment-certificate links from verified harvest solutions.
Visible ranking charged 1,892 primitive executions as an upper bound.

## Candidate outcomes

| Index | Kind | Development change | Admission change | Decision |
| --- | --- | ---: | ---: | --- |
| 0 | add_fragment | +0.000 pp | +0.000 pp | no_development_gain |
| 1 | add_fragment | +0.000 pp | not evaluated | not_selected |

Only the development winner gets the admission test. Acceptance requires positive development gain and no net admission regression.

## Proposal 0

`Concat(Sub(C4,C-5), Sub(C6,C-5))`

Candidate score: 10/16. Accepted: **False**.
Development wins: none.
Development losses: none.
Admission wins: none.
Admission losses: none.

Parameter changes: `{}`.
Library additions: ['Concat(Sub(C4,C-5), Sub(C6,C-5))'].
Visible-compatible tasks: 2; supporting certificates: 1; atoms: 2.
Evidence records marked as scrambled: 0/1.

Source certificate links (request hash / task ID; full provenance is in the snapshot):

- `46f2fbc1a6293fcf1284733e91bed33cfc8643ad2ae34724427c891df9c72cac` / `95d51d7dda0ef8dadb45`

Candidate evaluation request: `876d80ec8fbad3748e9e75b4f6d38417ae473b561fad097238c1b0f0df6d8725`.
Parent evaluation request: `171f25e7624efe695da6e75f7ff960e20f93b515bf9bfca8a2a294ff32fdaeaf`.
Candidate logical charges, including replay: `{"incidents": 0, "model_proposal_checks": 0, "oracle_string_executions": 256, "primitive_executions": 155770, "replay_batches": 1, "search_expansions": 3196, "wall_seconds": 0.41872390001663007, "worker_batches": 2}`.

## Proposal 1

`Concat(' ', '/')`

Candidate score: 10/16. Accepted: **False**.
Development wins: none.
Development losses: none.

Parameter changes: `{}`.
Library additions: ["Concat(' ', '/')"].
Visible-compatible tasks: 1; supporting certificates: 1; atoms: 2.
Evidence records marked as scrambled: 0/1.

Source certificate links (request hash / task ID; full provenance is in the snapshot):

- `ef39eb775a2dbdc4295280bb3d75e3489e5db474127b05d9f785b561aca1e462` / `7c29319a3d1fc712f8d5`

Candidate evaluation request: `6149d9e0888532ddbab957d86225c3690b349b87a07452ed337e5ddc1669d664`.
Parent evaluation request: `171f25e7624efe695da6e75f7ff960e20f93b515bf9bfca8a2a294ff32fdaeaf`.
Candidate logical charges, including replay: `{"incidents": 0, "model_proposal_checks": 0, "oracle_string_executions": 256, "primitive_executions": 155762, "replay_batches": 1, "search_expansions": 3196, "wall_seconds": 0.41846600000280887, "worker_batches": 2}`.

## Provenance

Journal: 2404 events; final hash `ac2da801b3e6785bd9d40df59079a0dcaf2ff8bd2b73861098ca95e2c5fcab8f`.
Proposal event: 434 / `57bcc446e6eb771b656cc2d08673495ae2e1cd74eb1a036e21db6e6c8eedd534`.
Resolution event: 440 / `34f5a071cd44c2e5973751e4ca91e690d453d3537cd706ed30c513ae8bfb22a3`.
Memory: `61ab746c2e9f307e7f7f444c15020b28e47ac6fc647ed1425a1fa54ef5206b96`.
Explanation script: `b629437e5734b8fc866dd1d138d74c811768ae42d80e23747e5e8972b50472d4`.

Finite admission examples can miss regressions. Hashes detect changes but do not authenticate the host. Artifact gains alone do not demonstrate a better improver or RSI.
