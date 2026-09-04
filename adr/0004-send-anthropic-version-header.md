# 0004. Send the `anthropic-version` header on every request

- **Status:** Accepted
- **Date:** 2026-09-04
- **Deciders:** PaperMtn
- **Tags:** transport, auth, spec-drift

---

## Context

Phase 0 decided the SDK would **not** send `anthropic-version`. The
recorded reasoning (CONTEXT.md § Spec anchors, and the comment on
`tests/test_transport.py::test_sync_does_not_inject_anthropic_version_header`)
was that only `x-api-key` was listed as required, and that production
`/v1/compliance/*` routes returned 404 when the Messages-API
`anthropic-version` header was present. Two tests asserted its absence,
which made the omission deliberate and load-bearing rather than an
oversight.

The hosted docs now contradict this in several places. The Compliance
API overview states every endpoint "takes the `anthropic-version` header
on every request", there is a dedicated Versioning section saying the
same, and every cURL example across all nine guide pages sends
`anthropic-version: 2023-06-01`.

Two facts shape the decision. First, the original 404 observation was
never re-confirmed after the docs were restructured, so it may describe
behaviour that no longer exists — or a request shape that was wrong for
some other reason. Second, this header is on *every* request the SDK
makes, so getting it wrong breaks the entire library rather than one
endpoint. That asymmetry means the change needs an escape hatch, not
just a flag day.

## Decision

We will send `anthropic-version: 2023-06-01` on every request by
default, exposed as an `anthropic_version` constructor keyword on both
clients and threaded to the transport like every other config value.
Passing `anthropic_version=None` suppresses the header entirely.

The hosted docs are the authoritative source under decision 17, and they
are unambiguous here. Continuing to omit a header that every published
example sends means the SDK is the only client on that path, which is
the position most likely to break silently. The `None` escape hatch
means that if the 404 behaviour does resurface, callers can work around
it in one keyword rather than waiting for a release.

## Consequences

- **Positive** — requests match the documented contract and every
  published example. Version pinning becomes available to callers, which
  matters when Anthropic ships a new API version.
- **Negative** — reverses a decision that was taken from observed live
  behaviour, on the strength of documentation alone. If the 404 does
  still reproduce, every request fails rather than one endpoint, which is
  the worst possible blast radius.
- **Follow-ups** — the two transport tests that asserted the header's
  absence are inverted, and two more cover the override and the `None`
  suppression. The `/v1/compliance/*` integration suite must be run
  against a live key before 0.3.0 ships; a 404 there is the signal to
  reopen this ADR. CONTEXT.md § Spec anchors is corrected.

## Alternatives considered

### Keep omitting the header

- **Why it was attractive:** it is the status quo, it is backed by a real
  observation against production, and it currently works.
- **Why it was rejected:** the observation is unverified against the
  current API and contradicted by every page of the current docs. "It
  works today" is not evidence that it keeps working, and a client that
  diverges from every documented example is carrying risk it cannot see.

### Send it, with no way to turn it off

- **Why it was attractive:** simpler surface, one less keyword to
  document, and no way for a caller to get into a half-configured state.
- **Why it was rejected:** the blast radius. If the header does break
  `/v1/compliance/*` for some caller or some route, an escape hatch turns
  a broken install into a one-line workaround.

### Verify against production first, then decide

- **Why it was attractive:** it settles the factual disagreement instead
  of choosing a side, and was the original plan.
- **Why it was rejected:** deferred rather than rejected. The
  maintainer chose to follow the docs now and let the integration run
  serve as the verification, which keeps Phase 1 moving. The test is
  still required before release.

## References

- Compliance API overview and Versioning sections, hosted docs
  (`spec-snapshots/2026-09-04/compliance-api.md`).
- Every cURL example in `spec-snapshots/2026-09-04/compliance-*.md`.
- CONTEXT.md decision 17 (hosted spec is authoritative).
- Supersedes the Phase-0 header decision recorded in CONTEXT.md
  § Spec anchors.
