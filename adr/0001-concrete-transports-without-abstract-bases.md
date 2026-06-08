# 0001. Concrete transports without abstract bases

- **Status:** Accepted
- **Date:** 2026-05-13
- **Deciders:** @PaperMtn
- **Tags:** transport, layering

---

## Context

Phase 1 scaffolded `BaseTransport` and `BaseAsyncTransport` as
`abc.ABC` classes under `_internal/`. Resources type-hinted those
bases so they could be instantiated with whichever concrete transport
the public client supplied. Pagination helpers did the same.

Phase 2.2 added the single concrete adapters — `SyncTransport` wrapping
`httpx.Client` and `AsyncTransport` wrapping `httpx.AsyncClient` — and
wired them into `ComplianceClient` / `AsyncComplianceClient`. No second
implementation exists. Phase 3.5's download helpers will reuse the same
transports via `stream=True`, not via a second adapter. The integration
test approach is to subclass the concrete transport or patch
`.request()` on the instance; both work without an ABC.

The post-3.1 architecture review applied the deletion test: removing
the ABCs concentrates zero complexity. Resources still get a typed
parameter; tests still substitute fakes the same way. The bases were
anticipating variability that did not materialise.

## Decision

**We delete `BaseTransport` and `BaseAsyncTransport`. Resources,
pagination helpers, and tests type-hint the concrete `SyncTransport` /
`AsyncTransport` classes directly.** If a second transport
implementation arrives (a recording transport for fixtures, an
alternative HTTP client, etc.), we introduce a `Protocol` type at that
point — not an ABC. The Protocol gives mypy structural-subtyping
support without forcing inheritance, and only earns its keep when
there is genuinely more than one shape behind it.

The principle in one line: **one adapter = hypothetical seam. Two
adapters = real seam.** Defer the seam until the second implementation
forces it.

## Consequences

- **Positive — leverage and locality:** the resource type-hints match
  the runtime types they receive. The transport stack reads top-to-
  bottom with no abstract layer to skip past. One less file under
  `_internal/`.
- **Positive — fewer paired edits:** a change to the request signature
  no longer has to land on three classes (`BaseTransport`,
  `SyncTransport`, the concrete `httpx.Client` method) — only on the
  concrete class.
- **Negative — fakes that skip `httpx.Client`:** a future test that
  wants a transport-shaped fake without constructing `httpx.Client`
  must either subclass and override `__init__` or duck-type with
  `Any`. Today this affects zero code. When the first such fake
  arrives, the right move is the Protocol described above.
- **Follow-up:** when a second transport implementation arrives, this
  ADR is superseded by a new one that introduces the Protocol seam.

## Alternatives considered

### Keep the ABCs as-is

- **Why it was attractive:** forward-looking flexibility; resources
  have a clean abstract interface to type against; a future second
  implementation slots in without churn.
- **Why it was rejected:** the deletion test pass. One adapter is a
  hypothetical seam. The ABC charges every reader and every change to
  the request signature for variability that does not exist. The
  cleaner move is to add the seam exactly when its second
  implementation exists.

### Replace ABCs with `Protocol` types now

- **Why it was attractive:** keeps a typed seam available without the
  inheritance ceremony of ABCs; future fakes can match the Protocol
  without subclassing.
- **Why it was rejected:** the same hypothetical-seam problem under a
  different name. A Protocol with one matching class today is no
  cheaper to maintain than an ABC with one subclass. Future ADR
  introduces the Protocol when the second matching class shows up.

## References

- Architecture-review walkthrough, 2026-05-13.
- Commit `e6e1dc1` — the implementation.
- Related: [ADR-0002](0002-response-dataclass-parsing-via-dataclasses-fields.md)
  applies the same "wait until N=2" principle to response parsing.
