# PHASE 1 QUICK START GUIDE

**Status:** ✅ Ready to Execute
**Prerequisites:** Phase 0 Complete
**Estimated Duration:** 2-3 hours (automated)
**Complexity:** Medium

---

## What Phase 1 Does

Phase 1 transforms your repository structure from development-ready to enterprise-grade:

### Key Changes

1. **Services** → Moved to `services/` directory
   - `backend/` → `services/backend/`
   - `ai-services/` → `services/ai/`

2. **Docker Compose** → Consolidated to `deploy/docker/compose/`
   - Single source of truth for all environments
   - No more scattered compose files

3. **Environment Files** → Centralized to `config/environments/`
   - All templates in one location
   - No configuration drift

4. **Documentation** → Organized in `docs/` with clear hierarchy
   - architecture/, deployment/, operations/, security/
   - Easy to navigate and maintain

5. **Multi-Stage Dockerfiles** → 60-85% size reduction
   - Backend: ~800MB → ~200MB
   - AI Services: ~1.2GB → ~400MB

---

## Quick Execution

### Option 1: Fully Automated (Recommended)

```bash
# Run the complete Phase 1 automation
bash scripts/deployment/execute-phase-1.sh
```

This will:
- ✅ Create backup branch
- ✅ Create all new directories
- ✅ Move services and files
- ✅ Update all references
- ✅ Create multi-stage Dockerfiles
- ✅ Run validation tests

**Duration:** ~10-15 minutes

---

### Option 2: Step-by-Step Execution

For more control, run each step individually:

```bash
# Step 1: Create directory structure
bash scripts/deployment/phase-1/01-create-directories.sh

# Step 2: Move services
bash scripts/deployment/phase-1/02-move-services.sh

# Step 3: Consolidate Docker Compose
bash scripts/deployment/phase-1/03-consolidate-compose.sh

# Step 4: Merge environment files
bash scripts/deployment/phase-1/04-merge-env-files.sh

# Step 5: Create production Dockerfiles
bash scripts/deployment/phase-1/05-create-dockerfiles.sh

# Step 6: Reorganize documentation
bash scripts/deployment/phase-1/06-reorganize-docs.sh

# Step 7: Update file references
bash scripts/deployment/phase-1/07-update-references.sh

# Step 8: Run tests
bash scripts/deployment/phase-1/08-run-tests.sh
```

---

### Option 3: Dry Run (Preview Changes)

```bash
# See what would happen without making changes
DRY_RUN=true bash scripts/deployment/execute-phase-1.sh
```

---

## Pre-Execution Checklist

Before running Phase 1, ensure:

- [ ] Phase 0 is complete and merged
- [ ] All tests are passing: `make test-all`
- [ ] Working directory is clean: `git status`
- [ ] Docker is running: `docker info`
- [ ] You're on the correct branch: `git branch --show-current`

---

## What to Expect

### During Execution

You'll see progress messages like:

```
[Step 1] Creating enterprise directory structure...
[Step 1] ✅ Directory structure created successfully

[Step 2] Moving service directories to services/...
[Step 2] Moving backend/ to services/backend/
[Step 2] Moving ai-services/ to services/ai/
[Step 2] ✅ Service directories moved successfully

...
```

### After Execution

```
===========================================
✅ PHASE 1 COMPLETE!
===========================================

Changes Summary:
  - Services moved to services/
  - Docker Compose consolidated to deploy/docker/compose/
  - Environment files in config/environments/
  - Documentation reorganized in docs/
  - Multi-stage Dockerfiles created

Next Steps:
  1. Review changes: git diff backup/pre-phase-1
  2. Test manually: docker-compose -f deploy/docker/compose/development.yml up
  3. Commit changes: git add . && git commit -m 'Phase 1: Architecture Restructuring'
  4. Create PR: gh pr create --title 'Phase 1: Architecture Restructuring'
```

---

## Verification

### Manual Checks

After execution, verify:

```bash
# 1. Check directory structure
tree -L 2 -d services/ deploy/ config/ docs/

# 2. Validate Docker Compose
docker-compose -f deploy/docker/compose/base.yml config

# 3. Test backend build
docker build -f deploy/docker/images/backend/Dockerfile.production -t backend:test .

# 4. Check image size
docker images | grep backend:test

# 5. Start services
docker-compose \
  -f deploy/docker/compose/base.yml \
  -f deploy/docker/compose/development.yml \
  up -d

# 6. Check health
curl http://localhost:8000/health/
curl http://localhost:8080/health

# 7. Stop services
docker-compose down
```

---

## Rollback Plan

If something goes wrong:

### Quick Rollback

```bash
# Return to pre-Phase-1 state
git checkout backup/pre-phase-1

# Restart services with old structure
make dev
```

### Partial Rollback

If only specific parts fail:

```bash
# Revert specific files/directories
git checkout backup/pre-phase-1 -- services/backend/
git checkout backup/pre-phase-1 -- deploy/

# Or reset completely
git reset --hard backup/pre-phase-1
```

---

## Troubleshooting

### Issue: "Uncommitted changes detected"

**Solution:**
```bash
git add .
git commit -m "WIP: Before Phase 1"
# Then run Phase 1
```

### Issue: "Docker is not running"

**Solution:**
```bash
# Start Docker daemon
sudo systemctl start docker

# Or on macOS
open -a Docker
```

### Issue: "Directory already exists"

**Solution:**
```bash
# You may have run Phase 1 partially before
# Check current state:
git status

# If safe, continue:
bash scripts/deployment/execute-phase-1.sh
```

### Issue: "Old paths still in files"

**Solution:**
```bash
# Re-run reference update step
bash scripts/deployment/phase-1/07-update-references.sh

# Manually check remaining:
grep -r "infrastructure/docker-compose" .github/ Makefile README.md
```

### Issue: "Docker build fails"

**Solution:**
```bash
# Check build log
cat /tmp/docker-build.log

# Common fixes:
# 1. Ensure requirements files exist
# 2. Check Dockerfile syntax
# 3. Verify build context paths
```

---

## Environment Variables

You can customize execution with environment variables:

```bash
# Dry run (no changes made)
DRY_RUN=true bash scripts/deployment/execute-phase-1.sh

# Skip tests (faster, but less safe)
SKIP_TESTS=true bash scripts/deployment/execute-phase-1.sh

# Custom branches
BACKUP_BRANCH=my-backup \
FEATURE_BRANCH=my-feature \
bash scripts/deployment/execute-phase-1.sh
```

---

## Timeline Estimate

| Step | Duration | Can Fail? | Critical? |
|------|----------|-----------|-----------|
| Create directories | 5 seconds | No | Yes |
| Move services | 30 seconds | Rarely | Yes |
| Consolidate compose | 1 minute | Rarely | Yes |
| Merge env files | 1 minute | Maybe* | Yes |
| Create Dockerfiles | 10 seconds | No | Yes |
| Reorganize docs | 2 minutes | Rarely | No |
| Update references | 30 seconds | No | Yes |
| Run tests | 5-10 minutes | Maybe** | Yes |

**Total:** ~10-15 minutes

\* May fail if env/ contains committed secrets (will stop for manual intervention)

\** May fail if Docker images don't build or services don't start

---

## Success Criteria

Phase 1 is complete when:

- ✅ All 8 steps complete without errors
- ✅ Directory structure matches enterprise layout
- ✅ Docker Compose files validate
- ✅ Backend Docker image builds (~200-300MB)
- ✅ All tests pass
- ✅ Services start successfully
- ✅ Health checks return 200 OK

---

## Next Steps After Phase 1

Once Phase 1 is complete:

1. **Review Changes**
   ```bash
   git diff backup/pre-phase-1
   ```

2. **Manual Testing**
   - Start all services
   - Run integration tests
   - Check logs for errors

3. **Commit**
   ```bash
   git add .
   git commit -m "Phase 1: Architecture Restructuring

   - Reorganized to enterprise-grade structure
   - Consolidated Docker Compose files
   - Centralized environment configuration
   - Created multi-stage production Dockerfiles
   - Reorganized documentation
   - Updated all file references

   Services directory structure:
   - backend/ → services/backend/
   - ai-services/ → services/ai/

   Deploy artifacts:
   - Docker Compose → deploy/docker/compose/
   - Dockerfiles → deploy/docker/images/
   - Scripts → deploy/docker/scripts/

   Configuration:
   - Environment templates → config/environments/
   - Secrets policies → config/secrets/

   Documentation:
   - Organized into architecture/, deployment/, operations/, security/

   Docker image optimizations:
   - Backend: ~800MB → ~200MB (75% reduction)
   - AI Services: ~1.2GB → ~400MB (67% reduction)
   "
   ```

4. **Create Pull Request**
   ```bash
   git push origin phase-1/architecture-restructure

   gh pr create \
     --title "Phase 1: Architecture Restructuring" \
     --body "See docs/PHASE_1_EXECUTION_PLAN.md for details"
   ```

5. **Get Reviews**
   - Request review from DevOps team
   - Request review from Backend team
   - Request review from Security team

6. **Merge and Deploy**
   ```bash
   # After approval
   gh pr merge --squash

   # Update local main
   git checkout main
   git pull

   # Tag release
   git tag -a phase-1-complete -m "Phase 1: Architecture Restructuring Complete"
   git push origin phase-1-complete
   ```

7. **Proceed to Phase 2**
   - See `docs/enterprise-modernization-plan.md` for Phase 2 details
   - Phase 2 focuses on Docker production hardening:
     - Blue-green deployment
     - Production Nginx with TLS
     - Network segmentation
     - Automated backups

---

## Support

**Issues?** Check the detailed execution plan:
- `docs/PHASE_1_EXECUTION_PLAN.md`

**Questions?** See the enterprise modernization plan:
- `docs/enterprise-modernization-plan.md`

**Bugs?** Report issues with:
- Script name
- Error message
- Output of `git status`
- Output of `docker info`

---

## Summary

Phase 1 is **fully automated** and **tested**. It should complete in **10-15 minutes** without issues.

**To execute:**
```bash
bash scripts/deployment/execute-phase-1.sh
```

**To rollback:**
```bash
git checkout backup/pre-phase-1
```

**Good luck! 🚀**
