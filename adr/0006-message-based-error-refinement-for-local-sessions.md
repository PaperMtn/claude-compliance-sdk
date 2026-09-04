# 0006. Message-based error refinement for local sessions

- **Status:** Accepted
- **Date:** 2026-09-04
- **Deciders:** PaperMtn
- **Tags:** exceptions, retry, sessions

---

## Context

The Compliance API error documentation is explicit: *"Match on
`error.type`, not on the message string. Messages are stable enough to
copy into runbooks but might be reworded over time; the type values are
part of the API contract."* The SDK follows that rule everywhere.

The local session endpoints are the documented exception. The same page
says: *"The local session endpoints have a few documented exceptions
where responses that share a type are told apart by their message."*
Two of those matter to us, because in both cases the type alone leads a
caller to do the wrong thing.

**A 404 that does not mean "gone".** While local sessions are
unavailable to a parent organisation, *every* call — including the list
— returns 404 `not_found_error` with the message `Local sessions are not
available.` It does not depend on the session ID and it can be
temporary. A caller treating it as an ordinary `NotFoundError` would
follow the documented advice for 404 ("the resource was deleted or never
existed; remove it from your queue") and discard a queue of perfectly
valid session IDs.

**A 503 that is not transient.** Three distinct conditions on the local
session endpoints return 503 `overloaded_error`. Two are transient and
say "Try again shortly." The third — a retention or data-handling
setting that cannot be evaluated — says "Try again later", depends on
the organisation's settings rather than load, and the docs warn it "can
persist for an extended period" with the instruction not to hold a walk
open waiting for it. Our retry policy has 503 in `RETRYABLE_STATUSES`,
so all three burn the full retry budget with backoff.

## Decision

We will refine these two conditions by message substring in
`APIError.from_response`, producing `LocalSessionsUnavailableError`
(subclass of `NotFoundError`) and `LocalSessionsRetentionUnavailableError`
(subclass of `InternalServerError`). The latter carries a class-level
`retryable = False`, a new marker on `APIError` that the transport passes
to `RetryPolicy.should_retry_status` to suppress a retry the status set
would otherwise allow.

Both classes are subclasses of the error the caller would previously
have caught, so existing `except NotFoundError` and
`except InternalServerError` handlers keep working — this only adds
precision for callers who want it. Matching is on a short distinctive
substring (`local sessions are not available`, `retention overrides`)
rather than the full sentence, so a rewording of the surrounding prose
does not silently drop the refinement. The precedence in
`should_retry_status` puts the server's `x-should-retry` header above
our marker: an explicit server signal is part of the contract and must
win over a local heuristic.

## Consequences

- **Positive** — a caller walking a queue of session IDs can distinguish
  "this endpoint is off right now, keep your queue" from "this session is
  gone, drop it", which is the difference between a resumable export and
  a lossy one. The non-transient 503 fails fast instead of spending four
  attempts and ~20 seconds of backoff per session.
- **Negative** — the SDK now depends on message wording in two places,
  against the API's own general advice. If Anthropic rewords either
  message past the substring we match, the refinement degrades silently:
  the caller gets the plain parent class and the old behaviour, which is
  the safe direction to fail but is invisible.
- **Follow-ups** — the `retryable` marker is a general mechanism; resist
  using it for anything that `error.type` can already distinguish.
  CLAUDE.md and CONTEXT.md record that message matching is confined to
  these two cases. If the integration run shows either message has
  changed, update the constants in `exceptions.py` rather than adding a
  second pattern.

## Alternatives considered

### Match on `error.type` only, and accept the imprecision

- **Why it was attractive:** it is exactly what the API documentation
  tells clients to do, and it keeps the exception taxonomy free of
  string matching.
- **Why it was rejected:** `error.type` genuinely cannot distinguish
  these cases — that is why the docs carve out the exception. Following
  the general rule here produces a client that discards valid work
  queues and retries a permanent failure.

### Expose the raw message and let callers match it themselves

- **Why it was attractive:** no SDK-side heuristics, and
  `error_message` is already on every `APIError`.
- **Why it was rejected:** it pushes a documented API subtlety onto every
  user, and it cannot fix the retry problem at all — by the time the
  caller sees the exception, the transport has already burned the retry
  budget.

### Drop 503 from the retryable set entirely

- **Why it was attractive:** simplest possible change, no new marker.
- **Why it was rejected:** the other two 503 bodies are genuinely
  transient and the docs say to retry them with backoff. Removing 503
  would trade one wrong behaviour for another, across every endpoint
  rather than just this one.

## References

- `spec-snapshots/2026-09-04/compliance-errors.md` — "Match on
  `error.type`", the `Local session not found` section, and
  "Local sessions temporarily unavailable".
- [ADR-0005](0005-local-and-remote-sessions-are-separate-resource-groups.md)
  — why local sessions are their own resource group.
