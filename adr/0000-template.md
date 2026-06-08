# NNNN. <Short, present-tense title>

- **Status:** Proposed | Accepted | Deprecated | Superseded by [ADR-XXXX](XXXX-…md)
- **Date:** YYYY-MM-DD
- **Deciders:** <names or GitHub handles>
- **Tags:** <e.g. transport, pagination, auth>

> **How to use this template**
>
> Copy this file to `adr/NNNN-short-slug.md` where `NNNN` is the
> next four-digit number. Fill in each section, then delete this blockquote
> and any unused optional sections. Keep the file short — an ADR is the
> *argument*, not a manual. If it grows past ~2 pages, you are probably
> mixing in implementation detail that belongs in code comments or
> CONTEXT.md.
>
> When the ADR is accepted, add a row to the decision-log table in
> `CONTEXT.md` pointing here.

---

## Context

What is the situation that forces a decision? Include only the facts that
constrain the choice — competing pressures, prior decisions, external
requirements, spec quirks. Avoid prescribing the answer here; that is what
the **Decision** section is for.

## Decision

The chosen option, stated in one or two sentences, in the active voice.
"We will …", not "It was decided that …". This is the load-bearing
sentence of the document — make it precise.

Follow up with a short paragraph explaining *why this option*, referencing
the trade-offs that ruled out the alternatives.

## Consequences

What becomes true once this decision is in effect? Cover both directions:

- **Positive** — what we gain.
- **Negative** — what we pay (added complexity, removed flexibility,
  ongoing maintenance, etc.).
- **Follow-ups** — work this decision creates (new tests, doc updates,
  deprecations, downstream ADRs).

## Alternatives considered

For each option that was seriously weighed but rejected:

### <Alternative name>

- **Why it was attractive:** …
- **Why it was rejected:** …

Two or three alternatives is usually enough. If there were no real
alternatives, say so explicitly — that itself is useful future context.

## References

- Spec section / page numbers, if relevant.
- Issues, PRs, or discussions that informed the decision.
- Related ADRs (`[ADR-XXXX](XXXX-…md)`).
- Prior art from other SDKs.
