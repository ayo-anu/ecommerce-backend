# 1. Adopt Monorepo Structure

Date: 2025-12-04

## Status

Accepted

## Context

We need to decide how to organize our codebase which consists of:
- Django REST API backend
- 7 FastAPI AI microservices
- Infrastructure as Code (Terraform, Docker Compose)
- Monitoring configurations
- Documentation

Options considered:
1. **Monorepo**: Single repository with all services
2. **Polyrepo**: Separate repository for each service
3. **Hybrid**: Backend in one repo, each AI service in separate repos

## Decision

We will use a **monorepo structure** with the following organization:

```
ecommerce-project/
├── backend/          # Django REST API
├── ai-services/      # All AI microservices
├── infrastructure/   # Docker Compose, env configs
├── k8s/             # Kubernetes manifests
├── terraform/        # Infrastructure as Code
├── monitoring/       # Prometheus, Grafana configs
├── tests/           # Integration tests
├── docs/            # Documentation
└── scripts/         # Utility scripts
```

## Consequences

### Positive

- **Atomic Changes**: Can update multiple services in a single commit/PR
- **Easier Refactoring**: Cross-service changes are simpler
- **Consistent Tooling**: One set of CI/CD, linting, testing configs
- **Simplified Dependencies**: Shared libraries easier to manage
- **Better Code Sharing**: `ai-services/shared/` for common code
- **Single Source of Truth**: Documentation and config in one place
- **Easier Onboarding**: New developers clone one repo

### Negative

- **Larger Repository**: Longer clone times (mitigated by sparse checkout)
- **Build Complexity**: Need to detect which services changed
- **Potential for Coupling**: Easier to create tight coupling between services
- **CI/CD Complexity**: Need smart caching and selective builds

### Neutral

- **Requires Discipline**: Need clear boundaries between modules (enforced via linting)
- **Folder Structure Standards**: Documented in `docs/MONOREPO_STRUCTURE.md`

## Alternatives Considered

### Polyrepo (Separate Repositories)

**Rejected** because:
- Cross-service changes require multiple PRs
- Dependency management becomes complex
- Difficult to maintain consistency
- Integration testing across services is harder
- More overhead for small team

### Hybrid Approach

**Rejected** because:
- Worst of both worlds
- Still have coordination overhead
- Unclear where shared code lives

## Implementation

1. ✅ Repository restructured with clear module boundaries
2. ✅ Documentation created (`docs/MONOREPO_STRUCTURE.md`)
3. ✅ Boundary enforcement script (`scripts/verify_structure.py`)
4. ✅ CI configured for selective builds based on changed files
5. ✅ Import linting rules to prevent circular dependencies

## References

- [Monorepo vs Polyrepo](https://monorepo.tools/)
- [Google's Monorepo](https://research.google/pubs/pub45424/)
- [Advantages of Monorepos](https://danluu.com/monorepo/)
