# OPA Policy Tests

## Overview

This directory contains test configurations for validating OPA security policies.

## Prerequisites

Install conftest:

```bash
# Linux/WSL
wget https://github.com/open-policy-agent/conftest/releases/download/v0.49.1/conftest_0.49.1_Linux_x86_64.tar.gz
tar xzf conftest_0.49.1_Linux_x86_64.tar.gz
sudo mv conftest /usr/local/bin/

# macOS
brew install conftest

# Verify installation
conftest --version
```

## Running Tests

### Test All Policies

```bash
# From project root
./scripts/security/test-policies.sh --all
```

### Test Specific Files

```bash
# Test a specific Dockerfile
./scripts/security/test-policies.sh --dockerfile deploy/docker/images/backend/Dockerfile.production

# Test a specific compose file
./scripts/security/test-policies.sh --compose deploy/docker/compose/production.yml
```

### Test Example Configurations

```bash
# Good examples (should pass)
conftest test config/policies/tests/good-dockerfile --policy config/policies/docker.rego --namespace docker
conftest test config/policies/tests/good-compose.yml --policy config/policies/compose.rego --namespace compose

# Bad examples (should fail)
conftest test config/policies/tests/bad-dockerfile --policy config/policies/docker.rego --namespace docker
conftest test config/policies/tests/bad-compose.yml --policy config/policies/compose.rego --namespace compose
```

## Test Files

### Good Examples
- `good-dockerfile` - Dockerfile that passes all policies
- `good-compose.yml` - Compose file that passes all policies

### Bad Examples
- `bad-dockerfile` - Dockerfile with violations
- `bad-compose.yml` - Compose file with violations

## Expected Results

When testing with conftest:

**Good files should output:**
```
✓ Policy check passed
```

**Bad files should output violations:**
```
FAIL - Line X: [violation message]
```

## CI Integration

Policies are automatically tested in CI via `.github/workflows/policy-check.yml` on:
- Pull requests modifying Dockerfiles or compose files
- Pushes to main and phase branches

## Troubleshooting

### Policy Syntax Errors

Check policy syntax:
```bash
conftest verify config/policies/docker.rego
conftest verify config/policies/compose.rego
```

### False Positives

If you encounter false positives:
1. Review the policy rules in `config/policies/*.rego`
2. Add exclusions if needed
3. Update documentation

### Policy Not Triggering

Ensure:
1. Policy namespace matches (`docker` or `compose`)
2. Input format is correct (conftest parses Dockerfile/YAML)
3. Policy rules match the input structure

## Writing New Tests

To add new test cases:

1. Create test file in this directory
2. Document expected behavior
3. Run test with conftest
4. Update this README

Example:
```bash
# Create test file
cat > config/policies/tests/test-my-rule << 'EOF'
FROM python:3.11-slim
# Test content
EOF

# Run test
conftest test config/policies/tests/test-my-rule --policy config/policies/docker.rego
```
