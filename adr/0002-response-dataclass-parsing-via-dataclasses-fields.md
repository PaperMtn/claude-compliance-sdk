# 0002. Response dataclass parsing via `dataclasses.fields`

- **Status:** Accepted
- **Date:** 2026-05-13
- **Deciders:** @PaperMtn
- **Tags:** parsing, dataclasses, conventions

---

## Context

Every Compliance API response type the SDK exposes follows the same
recipe: a handful of known top-level fields modelled as dataclass
attributes (`id`, `created_at`, `type`, etc.) plus
`extra: dict[str, Any]` capturing two flavours of leftover keys —
activity-type-specific fields (`claude_chat_id` on a
`claude_chat_created` activity, `scopes` on `api_key_created`, etc.)
and any new top-level fields a future spec revision adds.

The set of "known" keys is a property of the dataclass. The Phase 3.1
implementation of `Activity.from_dict` maintained that set twice — once
as the field annotations on the dataclass, once as
`_KNOWN_ACTIVITY_FIELDS = frozenset({...})` used to compute the
extras. A field added to the dataclass without a matching frozenset
update would silently land in both the typed attribute *and* `extra`;
the reverse would drop a known field on the floor.

With 10+ resource types ahead (`Chat`, `Project`, `File`,
`GeneratedFile`, `Artifact`, `Organization`, `Role`, `Group`, …) the
duplication compounds, and the per-class drift hazard is real.

## Decision

**We provide `parse_with_extra(cls, body)` in
`_internal/parsing.py`. It derives the known field set from
`dataclasses.fields(cls)`, copies matching body values to constructor
kwargs, and dumps the remaining body keys into `extra`.** Resource
dataclasses keep a one-line `from_dict` classmethod that delegates to
the helper.

The helper is **deliberately minimal**:

- **No per-field coercion hook.** If the server returns a type that
  does not match the annotation, the dataclass constructor accepts it
  verbatim. We trust the wire format.
- **No nested-type recursion.** Nested unions (e.g., the `Actor`
  union on `Activity`) are stored as raw dicts. Resources that want
  typed nested fields supply their own `from_dict`.
- **Free function, not mixin or base class.** Each dataclass writes
  one line of `from_dict` boilerplate; resolution is local to the
  class.

## Consequences

- **Positive — locality:** the known/unknown split becomes a property
  of the dataclass itself. Adding a field automatically updates the
  parser; no parallel frozenset to maintain.
- **Positive — leverage:** one helper, one set of tests, every future
  response dataclass benefits.
- **Positive — explicit resolution:** `Activity.from_dict(body)` reads
  as "this class parses itself, see `parse_with_extra`" rather than
  via inheritance from a hidden mixin.
- **Negative — no defence against server type drift:** if a future
  spec revision changes the type of a known field, the dataclass
  constructor accepts the new type without complaint. The fix when
  needed is a per-class override of `from_dict`, not a framework-wide
  change.
- **Negative — no help for nested unions:** Phase 3.1's `Actor` union
  remains `dict[str, Any]` on `Activity.actor`. Resources that want
  typed nested objects must build the discrimination themselves.
- **Follow-up:** when the first nested union genuinely needs typing
  (likely `Actor` on `Activity` or a similar shape on `Chat`), decide
  whether to extend the helper with a nested-type registry or keep
  the parsing per-resource. Either is fine; revisit at that point.

## Alternatives considered

### Mixin / base class providing `from_dict`

- **Why it was attractive:** removes the one-line `from_dict`
  boilerplate from each dataclass. `Activity(ExtraFieldsParser)` gets
  `Activity.from_dict(body)` for free.
- **Why it was rejected:** a reader following `Activity.from_dict`
  has to know it comes from a mixin one inheritance hop away —
  resolution is implicit. `@dataclass` ordering with a base class is
  also a subtle footgun (decorator must run after the base is
  inspected); future maintainers would forget. The free-function
  pattern keeps the indirection explicit at one cheap line per
  dataclass.

### Per-field coercion hook

- **Why it was attractive:** handles a hypothetical case where the
  server's wire type drifts from the dataclass annotation, without
  requiring a per-class override.
- **Why it was rejected:** anticipates variability that does not
  exist today. Per-field coercion belongs in a per-class `from_dict`
  if anywhere. Adding it framework-wide is exactly the
  hypothetical-seam anti-pattern [ADR-0001](0001-concrete-transports-without-abstract-bases.md)
  deletes. When a first real coercion need lands, we add it in the
  one class that needs it, not in the helper.

### Hand-maintained `_KNOWN_FIELDS` frozenset per dataclass

- **Why it was attractive:** explicit, no metaprogramming, easy to
  read.
- **Why it was rejected:** the drift hazard described in **Context**.
  Maintaining the known set twice (once as dataclass fields, once as
  the frozenset) is exactly the paired-edit hazard architecture
  review surfaces. The metaprogramming here is one stdlib call
  (`dataclasses.fields`) — not enough indirection to justify the
  paired edit.

## References

- Architecture-review walkthrough, 2026-05-13.
- Commit `74a4de6` — the implementation.
- Related: [ADR-0001](0001-concrete-transports-without-abstract-bases.md)
  establishes the "wait until N=2" principle this ADR follows.
