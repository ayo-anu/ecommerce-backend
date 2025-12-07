# Architecture Decision Records (ADRs)

## What is an ADR?

An **Architecture Decision Record** (ADR) is a document that captures an important architectural decision made along with its context and consequences.

## Why ADRs?

- **Memory**: Helps future developers understand why decisions were made
- **Alignment**: Gets team buy-in on significant decisions
- **Historical Context**: Documents the state of the world when decision was made
- **Prevents Revisiting**: Avoids rehashing old debates

## ADR Format

Each ADR should include:

1. **Title**: Short descriptive title
2. **Status**: Proposed, Accepted, Deprecated, Superseded
3. **Context**: What is the issue we're facing?
4. **Decision**: What did we decide?
5. **Consequences**: What are the positive and negative outcomes?

## Naming Convention

ADRs are numbered sequentially:
- `0001-use-django-rest-framework.md`
- `0002-adopt-microservices-architecture.md`
- `0003-use-stripe-for-payments.md`

## When to Write an ADR?

Write an ADR when you make a decision that:
- Is difficult or expensive to reverse
- Significantly impacts the system architecture
- Has trade-offs that need to be documented
- Future developers will need to understand

## ADR List

| # | Title | Status | Date |
|---|-------|--------|------|
| [0001](0001-monorepo-structure.md) | Adopt Monorepo Structure | Accepted | 2025-12-04 |
| [0002](0002-service-authentication.md) | Per-Service Authentication Keys | Accepted | 2025-12-04 |
| [0003](0003-payment-isolation.md) | Payment Data Isolation Strategy | Accepted | 2025-12-04 |
| [0004](0004-docker-compose-development.md) | Docker Compose for Development | Accepted | 2025-12-04 |
| [0005](0005-structured-logging.md) | Structured JSON Logging | Accepted | 2025-12-04 |

## Template

```markdown
# [Number]. [Title]

Date: YYYY-MM-DD

## Status

[Proposed | Accepted | Deprecated | Superseded by ADR-XXXX]

## Context

What is the issue that we're seeing that is motivating this decision or change?

## Decision

What is the change that we're proposing and/or doing?

## Consequences

What becomes easier or more difficult to do because of this change?

### Positive

- Benefit 1
- Benefit 2

### Negative

- Drawback 1
- Drawback 2

### Neutral

- Side effect 1

## Alternatives Considered

### Alternative 1
Why it was rejected...

### Alternative 2
Why it was rejected...
```

## Contributing

1. Copy the template above
2. Number it sequentially
3. Fill out all sections
4. Get team review
5. Merge when accepted
6. Update this README with link

## References

- [ADR GitHub Organization](https://adr.github.io/)
- [Michael Nygard's ADR Article](https://thinkrelevance.com/blog/2011/11/15/documenting-architecture-decisions)
