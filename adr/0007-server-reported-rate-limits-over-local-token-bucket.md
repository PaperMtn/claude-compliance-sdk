# 0007. Server-reported rate limits over a local token bucket

- **Status:** Accepted
- **Date:** 2026-09-04
- **Deciders:** PaperMtn
- **Tags:** transport, rate-limiting, retry

---

## Context

The SDK has always shipped a `SlidingWindowLimiter` defaulting to 600
requests per minute, matching the documented server limit. It is blind:
it counts only the requests this client instance made.

The real limit is **shared across every key under a parent
organisation** and across every `/v1/compliance/*` endpoint. So a local
counter is wrong in both directions. Two workers each pacing themselves
at 600 rpm will together sail past the budget, while a single worker
that is the only consumer never learns it had headroom. v0.2.0
acknowledged this in the docstrings — "best-effort and per-client" —
without being able to do anything about it.

The API now reports the budget on every authenticated response:
`anthropic-ratelimit-requests-limit`,
`anthropic-ratelimit-requests-remaining`, and
`anthropic-ratelimit-requests-reset` (an RFC 3339 timestamp). The
documentation is explicit that these exist "so your client can throttle
proactively instead of waiting for a 429".

Two further wrinkles came out of the same docs. The remote-session
endpoints carry a **second** budget on top of the shared one, whose 429
always sends `retry-after: 1` as *a minimum wait, not the actual reset
time* — and whose `anthropic-ratelimit-*` headers describe the shared
limit rather than the budget that was actually exhausted. Separately,
the documented fallback for a 429 with no `Retry-After` is "start at 1
second, double up to 60 seconds", where the SDK's defaults were 0.5s
and 20s.

## Decision

We will consume the `anthropic-ratelimit-*` headers on every response
and let them constrain the limiter, keeping the local window as an
upper bound. Concretely:

- The transport parses the three headers into a `RateLimitSnapshot` and
  hands it to the limiter after every response, success or error. A 403
  consumes a quota unit, so error responses matter.
- When the server reports `remaining == 0` with a future reset,
  `acquire()` waits until that reset before letting the next request
  through. Turning a guaranteed 429 into a wait is strictly better than
  spending a request to discover it.
- The snapshot is exposed as `client.rate_limit_status`, so callers
  pacing their own worker pools can read `remaining` rather than
  reverse-engineering it.
- Server headers are honoured even when `rate_limit_rpm=0`. That flag
  opts out of the *local* window, which is a client-side convenience;
  the shared budget is not something a caller can opt out of.
- `retry_after` becomes a **floor** on the backoff rather than
  replacing it, and the backoff defaults move to 1s/60s to match the
  documented fallback.

Deliberately *not* done: any proportional slowdown as `remaining` gets
low. It is tempting, but every rule for it would be invented — the docs
give no guidance, and the right aggressiveness depends on how many
other consumers share the budget, which the SDK cannot know. Exposing
`remaining` lets callers implement the policy that suits their fleet.

## Consequences

- **Positive** — a client that shares a budget now slows down instead of
  discovering the ceiling with a 429. `remaining` is available for
  callers to pace on. The remote-session budget no longer burns the
  whole retry allowance in three seconds, because backoff escalates
  past the `retry-after: 1` floor.
- **Negative** — `acquire()` can now block on a server-reported deadline
  that the caller never configured, which is surprising if you passed
  `rate_limit_rpm=0` expecting no client-side waiting. The reset is
  converted to a monotonic deadline at observation time, so a snapshot
  taken just before a long pause can hold a stale deadline. Retries are
  slower by default than before (1s vs 0.5s first delay).
- **Follow-ups** — the reset header is parsed with
  `datetime.fromisoformat` after normalising a trailing `Z`; if the API
  ever sends an HTTP-date instead, that returns `None` and the
  refinement silently degrades to the local window. `RateLimitSnapshot`
  is now public API, so its fields cannot change shape without a
  breaking release.

## Alternatives considered

### Keep the local bucket only, and rely on 429 handling

- **Why it was attractive:** no new state, no new public type, and the
  retry path already honours `Retry-After` correctly.
- **Why it was rejected:** it wastes a request on every discovery of the
  limit, and it cannot help a fleet at all. The headers exist precisely
  so clients do not have to work this way.

### Throttle proportionally as `remaining` falls

- **Why it was attractive:** smoother than a hard stop at zero, and it
  would keep a busy client from ever hitting the wall.
- **Why it was rejected:** the thresholds and curve would be invented.
  With no guidance on what fraction to start backing off at, any
  default is as likely to hurt (needless slowdown for a sole consumer)
  as to help. Exposing `remaining` puts the decision where the
  information is.

### Drop the local limiter entirely now that the server reports

- **Why it was attractive:** one mechanism instead of two, and the local
  window is the one that is provably wrong.
- **Why it was rejected:** the headers only arrive *after* the first
  response, so a cold client bursting hundreds of requests in parallel
  has nothing to pace it. The local window is a useful floor for
  exactly the burst it was added for.

## References

- `spec-snapshots/2026-09-04/compliance-errors.md` — "429 Too Many
  Requests", the response-header list, the shared-budget description,
  and the remote-session second budget.
- CHANGELOG 0.2.0 — the earlier `rate_limit_rpm` clarification this
  supersedes.
- [ADR-0006](0006-message-based-error-refinement-for-local-sessions.md)
  — the `retryable` marker, the other retry-path refinement.
