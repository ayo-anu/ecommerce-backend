# Secret Scanning

## Overview

The e-commerce platform implements comprehensive secret scanning using multiple tools to prevent accidental exposure of sensitive credentials, API keys, and tokens in the codebase and git history.

## Defense in Depth Strategy

We use **three layers** of secret detection:

1. **Pre-commit Hooks**: Block secrets before they enter git
2. **CI/CD Pipeline**: Scan all code changes automatically
3. **Periodic Scans**: Regular full history scans

## Tools Used

| Tool | Purpose | Scope | When |
|------|---------|-------|------|
| **Gitleaks** | Primary scanner | All file types | Pre-commit + CI + History |
| **TruffleHog** | Verification | All file types | CI + History |
| **detect-secrets** | Additional coverage | Python/JSON | Pre-commit + CI |

## Implementation

### 1. Pre-commit Hooks

**Configuration**: `.pre-commit-config.yaml`

Automatically runs before every commit to catch secrets before they enter git.

#### Installation

```bash
# Install pre-commit
pip install pre-commit

# Install hooks
pre-commit install

# Run manually on all files
pre-commit run --all-files
```

#### What Gets Scanned

- **Gitleaks**: Full regex-based secret detection
- **detect-secrets**: Entropy-based detection + specific patterns
- **AWS Credentials**: Built-in AWS credential detector
- **Private Keys**: PEM format private keys

#### Bypass (Emergency Only)

```bash
# Skip pre-commit hooks (NOT RECOMMENDED)
git commit --no-verify -m "message"
```

**Warning**: Bypassing pre-commit hooks will cause CI to fail if secrets are present.

### 2. CI/CD Integration

**Workflow**: `.github/workflows/secret-scan.yml`

Runs automatically on:
- All pushes to any branch
- All pull requests
- Daily scheduled scan (2 AM UTC)
- Manual trigger

#### CI Scanners

**Gitleaks**:
```yaml
- uses: gitleaks/gitleaks-action@v2
  env:
    GITHUB_TOKEN: ${{ secrets.GITHUB_TOKEN }}
```

**TruffleHog**:
```yaml
- uses: trufflesecurity/trufflehog@main
  with:
    path: ./
    base: main
    head: HEAD
    extra_args: --debug --only-verified
```

**detect-secrets**:
```bash
detect-secrets scan --baseline .secrets.baseline
detect-secrets audit .secrets.baseline
```

#### Failure Handling

If secrets are detected:
1. ❌ CI fails immediately
2. 🚨 PR comment added with urgent warning
3. 📊 Detailed report generated
4. 🚫 Merge is blocked

### 3. Git History Scanning

**Script**: `scripts/security/scan-git-history.sh`

Scans entire git history for exposed secrets.

#### Usage

```bash
# Scan with Gitleaks (default)
./scripts/security/scan-git-history.sh

# Scan with TruffleHog
./scripts/security/scan-git-history.sh --trufflehog

# Scan with all tools
./scripts/security/scan-git-history.sh --all

# Verbose output
./scripts/security/scan-git-history.sh --all --verbose

# Custom report directory
./scripts/security/scan-git-history.sh --report-dir ./my-reports
```

#### When to Run

- Before major releases
- After onboarding new developers
- During security audits
- When secrets exposure is suspected

## Gitleaks Configuration

**File**: `.gitleaks.toml`

### Custom Rules

```toml
[[rules]]
id = "stripe-secret-key"
description = "Stripe Secret API Key"
regex = '''sk_(test|live)_[0-9a-zA-Z]{24,}'''
tags = ["stripe", "payment", "secret"]

[[rules]]
id = "openai-api-key"
description = "OpenAI API Key"
regex = '''sk-[A-Za-z0-9]{48}'''
tags = ["openai", "api", "secret"]
```

### Allowlist

Prevent false positives:

```toml
[allowlist]
paths = [
    '''.env.example$''',
    '''.*_test\.py$''',
    '''.*/tests/.*''',
    '''.*\.md$''',
]

regexes = [
    '''placeholder''',
    '''example''',
    '''dummy''',
    '''test''',
]
```

### Extending Configuration

Add new rules:

```toml
[[rules]]
id = "my-custom-api-key"
description = "My Service API Key"
regex = '''myservice_[a-zA-Z0-9]{32}'''
tags = ["custom", "api-key"]
```

## Secret Types Detected

### Payment Providers

- ✅ Stripe (secret, publishable, restricted keys)
- ✅ PayPal credentials
- ✅ Braintree tokens

### Cloud Providers

- ✅ AWS (access keys, secret keys, session tokens)
- ✅ Google Cloud (API keys, OAuth secrets)
- ✅ Azure (storage keys, connection strings)

### AI Services

- ✅ OpenAI API keys
- ✅ Anthropic API keys
- ✅ Hugging Face tokens

### Communication

- ✅ Slack webhooks & tokens
- ✅ SendGrid API keys
- ✅ Twilio API keys
- ✅ Mailgun API keys

### Development Tools

- ✅ GitHub tokens (PAT, OAuth, App)
- ✅ GitLab tokens
- ✅ Docker Hub tokens
- ✅ NPM tokens
- ✅ PyPI tokens

### Database

- ✅ Connection strings (PostgreSQL, MySQL, MongoDB, Redis)
- ✅ Database passwords
- ✅ Redis passwords

### General

- ✅ Private keys (RSA, EC, SSH)
- ✅ JWT secrets
- ✅ Generic API keys
- ✅ Bearer tokens

## Handling Detected Secrets

### If Secrets Are Detected

#### 1. Immediate Response

```bash
# DO NOT commit the changes
git reset HEAD~1  # If already committed locally

# Remove the secret from the file
vim path/to/file

# Use environment variables or Vault instead
export MY_SECRET="actual_secret_value"
```

#### 2. Rotate Credentials

**CRITICAL**: Assume the secret is compromised and rotate it immediately:

- API Keys: Generate new key in provider dashboard
- Passwords: Change password
- Tokens: Revoke and generate new token

#### 3. Remove from Git History

If secret was pushed to remote:

```bash
# Scan git history
./scripts/security/scan-git-history.sh --all

# Remove secret (interactive)
./scripts/security/remove-secrets-from-history.sh --pattern 'sk_live_[a-zA-Z0-9]+'

# Or remove entire file
./scripts/security/remove-secrets-from-history.sh --file .env

# Force push (WARNING: rewrites history)
git push origin --force --all
git push origin --force --tags
```

**Important**: All collaborators must re-clone after force push.

#### 4. Update Configuration

Add to `.gitignore`:
```
# Secrets
.env
.env.local
*.key
*.pem
secrets/
```

Add to `.gitleaks.toml` allowlist if false positive:
```toml
[allowlist]
regexes = [
    '''my-false-positive-pattern''',
]
```

## Removing Secrets from Git History

**Script**: `scripts/security/remove-secrets-from-history.sh`

### Prerequisites

Install BFG Repo-Cleaner:

```bash
# macOS
brew install bfg

# Linux
wget https://rtyley.github.io/bfg-repo-cleaner/releases/latest/bfg.jar
# Run with: java -jar bfg.jar
```

### Usage Examples

#### Remove API Key Pattern

```bash
./scripts/security/remove-secrets-from-history.sh \
    --pattern 'sk_live_[a-zA-Z0-9]+'
```

#### Remove File

```bash
./scripts/security/remove-secrets-from-history.sh \
    --file '.env'
```

#### Remove Multiple Passwords

Create `passwords.txt`:
```
password123===>***REMOVED***
oldapikey===>***REMOVED***
secrettoken===>***REMOVED***
```

Run:
```bash
./scripts/security/remove-secrets-from-history.sh \
    --passwords passwords.txt
```

#### Dry Run

```bash
./scripts/security/remove-secrets-from-history.sh \
    --pattern 'sk_test_.*' \
    --dry-run
```

### Post-Removal Steps

1. **Verify**: `git log --all --oneline -20`
2. **Test**: Run application to ensure nothing broke
3. **Rotate**: Change all affected credentials
4. **Push**: Force push to remote (see warnings in script output)
5. **Notify**: All team members must re-clone

## False Positives

### Common False Positives

1. **Example code in documentation**
   ```python
   # This triggers: api_key = "sk_test_example123..."
   # Solution: Add to allowlist or use placeholder text
   api_key = "YOUR_API_KEY_HERE"
   ```

2. **Test fixtures**
   ```python
   # Add to .gitleaks.toml allowlist
   paths = ['''.*_test\.py$''']
   ```

3. **Template variables**
   ```bash
   # These are OK
   API_KEY=${API_KEY}
   SECRET={{SECRET}}
   ```

### Handling False Positives

#### Method 1: Update Allowlist

`.gitleaks.toml`:
```toml
[allowlist]
paths = [
    '''docs/examples/.*''',
]

regexes = [
    '''pk_test_.*example''',  # Allow test examples
]
```

#### Method 2: Inline Comments

```python
# gitleaks:allow
api_key = "sk_test_1234567890abcdef"  # Example only
```

#### Method 3: Update Baseline

```bash
# Update detect-secrets baseline
detect-secrets scan --baseline .secrets.baseline --update
```

## Best Practices

### 1. Never Commit Secrets

✅ **Good**:
```python
import os
API_KEY = os.getenv('STRIPE_API_KEY')
```

❌ **Bad**:
```python
API_KEY = "sk_live_abc123xyz789"
```

### 2. Use Environment Variables

```bash
# .env (gitignored)
STRIPE_API_KEY=sk_live_actual_key
DATABASE_URL=postgresql://user:pass@localhost/db

# .env.example (committed)
STRIPE_API_KEY=sk_test_your_key_here
DATABASE_URL=postgresql://user:password@localhost/dbname
```

### 3. Use Secrets Management

```python
# Vault integration
from core.vault_client import get_secret_or_env

stripe_key = get_secret_or_env(
    vault_path='shared/stripe',
    vault_key='STRIPE_SECRET_KEY',
    env_var='STRIPE_SECRET_KEY'
)
```

### 4. Rotate Regularly

- **Automated**: Vault rotation (weekly)
- **Manual**: API keys (quarterly minimum)
- **On breach**: Immediately

### 5. Minimize Secret Scope

```yaml
# Good: Narrow permissions
STRIPE_API_KEY=rk_test_restricted_key  # Restricted key

# Bad: Excessive permissions
STRIPE_API_KEY=sk_live_full_access_key
```

### 6. Monitor and Audit

```bash
# Regular scans
./scripts/security/scan-git-history.sh --all

# Check pre-commit hooks are installed
pre-commit --version
ls -la .git/hooks/pre-commit

# Review CI logs
# Check GitHub Actions secret-scan.yml results
```

## Troubleshooting

### Pre-commit Hook Not Running

```bash
# Reinstall hooks
pre-commit uninstall
pre-commit install

# Verify installation
pre-commit run --all-files
```

### CI Failing with False Positives

1. **Update allowlist** in `.gitleaks.toml`
2. **Commit allowlist update**
3. **Re-run CI**

### Gitleaks Not Installed

```bash
# macOS
brew install gitleaks

# Linux
wget https://github.com/gitleaks/gitleaks/releases/download/v8.18.1/gitleaks_8.18.1_linux_x64.tar.gz
tar xzf gitleaks_8.18.1_linux_x64.tar.gz
sudo mv gitleaks /usr/local/bin/
```

### Secret Found in History

Follow the [Handling Detected Secrets](#handling-detected-secrets) section.

## Compliance Mapping

### PCI-DSS

| Requirement | Implementation | Evidence |
|-------------|---------------|----------|
| 3.4 - Protect stored data | Secret scanning prevents storage | CI logs, pre-commit |
| 8.2.1 - Render passwords unreadable | Secrets not in code | Scan results |
| 12.3 - Protect stored data | Automated detection | Workflows |

### SOC 2

| Control | Implementation | Evidence |
|---------|---------------|----------|
| CC6.1 - Logical access | Secret scanning | CI/CD logs |
| CC6.6 - Least privilege | Minimal secret exposure | Configuration |
| CC7.2 - Monitoring | Daily scans | Scheduled workflows |

## Integration with Security Audit

Secret scanning integrates with the comprehensive security audit:

```bash
# Full security audit (includes secret scan)
./scripts/security/security-audit.sh

# Just secret scanning
./scripts/security/scan-git-history.sh --all
```

## References

- [Gitleaks Documentation](https://github.com/gitleaks/gitleaks)
- [TruffleHog](https://github.com/trufflesecurity/trufflehog)
- [detect-secrets](https://github.com/Yelp/detect-secrets)
- [BFG Repo-Cleaner](https://rtyley.github.io/bfg-repo-cleaner/)
- [GitHub Secrets Documentation](https://docs.github.com/en/code-security/secret-scanning)

## Support

For issues with secret scanning:

1. Check this documentation
2. Review `.gitleaks.toml` configuration
3. Run manual scan: `./scripts/security/scan-git-history.sh --all --verbose`
4. Check pre-commit installation: `pre-commit run --all-files`
5. Review CI logs in GitHub Actions

---

**Last Updated**: 2024-12-19
**Version**: 1.0
**Owner**: Security & Platform Team
