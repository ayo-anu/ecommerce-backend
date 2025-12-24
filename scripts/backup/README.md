# Backup and Verification Scripts

This directory contains automated backup and disaster recovery scripts for the E-Commerce platform.

## Overview

The backup system implements a comprehensive 3-2-1 backup strategy:
- **3** copies of data (production + local backup + S3)
- **2** different storage types (local disk + S3)
- **1** offsite copy (S3 in different region)

## Scripts

### Backup Scripts

#### `backup-databases.sh`
Backs up PostgreSQL databases (main + AI) with compression and optional encryption.

**Usage:**
```bash
# Local backup only
./backup-databases.sh

# With S3 upload
./backup-databases.sh --s3-upload --s3-bucket ecommerce-backups-production

# With encryption
./backup-databases.sh --encrypt --s3-upload --s3-bucket ecommerce-backups-production
```

**Features:**
- pg_dumpall for complete database backup
- Gzip compression
- GPG encryption (optional)
- S3 upload with lifecycle management
- Automatic cleanup of old backups (7 days local retention)
- Backup manifest generation

#### `backup-media.sh`
Backs up media files from Docker volumes.

**Usage:**
```bash
./backup-media.sh --s3-upload --s3-bucket ecommerce-media-backups
```

#### `backup-redis.sh`
Backs up Redis RDB snapshots.

**Usage:**
```bash
./backup-redis.sh --s3-upload
```

### Verification Scripts

#### `verify-backup.sh` ⭐ **NEW**
Performs actual restore testing to verify backup integrity.

**Features:**
- Creates temporary Docker containers for testing
- Restores backups to test containers
- Verifies data integrity
- Tests PostgreSQL and Redis backups
- Generates verification reports
- Sends Slack/Email notifications on failure
- Automatic cleanup of test containers

**Usage:**
```bash
# Verify latest backups only (recommended for weekly tests)
./verify-backup.sh --latest

# Verify all backups from last 7 days
./verify-backup.sh --all

# Verify specific database
./verify-backup.sh --latest --database main

# With notifications
./verify-backup.sh --latest --notify

# Custom backup directory
./verify-backup.sh --backup-dir /custom/path --latest
```

**Environment Variables:**
```bash
export SLACK_WEBHOOK_URL="https://hooks.slack.com/services/YOUR/WEBHOOK/URL"
export NOTIFICATION_EMAIL="ops-team@example.com"
```

**Exit Codes:**
- `0` - All verifications passed
- `1` - One or more verifications failed
- `2` - Critical error (unable to run tests)

**Report Location:**
`/var/log/ecommerce/backup-verification/verification_YYYYMMDD_HHMMSS.log`

### Restore Scripts

#### `restore-database.sh`
Restores PostgreSQL databases from backup.

**Usage:**
```bash
# Restore latest local backup
./restore-database.sh --latest --database main

# Restore from S3
./restore-database.sh --from-s3 --s3-bucket ecommerce-backups-production --latest --database main

# Restore specific backup file
./restore-database.sh --file /backups/postgres/main_db_20251224_120000.sql.gz
```

**⚠️ Warning:** This will overwrite the current database. Always verify before running in production.

## Automated Setup

### `setup-backup-cron.sh` ⭐ **NEW**
Configures automated backup and verification cron jobs.

**Usage:**
```bash
# Install with S3 backups and notifications
sudo ./setup-backup-cron.sh \
    --s3-bucket ecommerce-backups-production \
    --notify-email ops-team@example.com \
    --slack-webhook https://hooks.slack.com/services/YOUR/WEBHOOK

# Install without S3 (local backups only)
sudo ./setup-backup-cron.sh

# Uninstall all cron jobs
sudo ./setup-backup-cron.sh --uninstall
```

**Automated Schedule:**
- PostgreSQL Backups: Every 6 hours (00:00, 06:00, 12:00, 18:00)
- Redis Backups: Daily at 04:00 AM
- Media Backups: Daily at 02:00 AM
- **Verification Tests: Weekly on Sunday at 03:00 AM** ⭐
- Health Checks: Daily at 08:00 AM

**Logs:**
- Backup logs: `/var/log/ecommerce/backup.log`
- Verification logs: `/var/log/ecommerce/backup-verification.log`
- Verification reports: `/var/log/ecommerce/backup-verification/`

## Disaster Recovery Testing

### Weekly Automated Verification

The system automatically performs weekly restore tests every Sunday at 3 AM:

1. Creates temporary PostgreSQL and Redis test containers
2. Restores latest backups to test containers
3. Verifies data integrity
4. Generates detailed verification report
5. Sends notifications on failure
6. Automatically cleans up test containers

### Manual Verification Test

To manually test backup restoration:

```bash
# Test latest backups
sudo /opt/ecommerce-platform/scripts/backup/verify-backup.sh --latest --notify

# Test all recent backups
sudo /opt/ecommerce-platform/scripts/backup/verify-backup.sh --all --notify
```

### Monitoring Verification Results

```bash
# View latest verification log
tail -f /var/log/ecommerce/backup-verification.log

# View specific verification report
ls -lth /var/log/ecommerce/backup-verification/
cat /var/log/ecommerce/backup-verification/verification_YYYYMMDD_HHMMSS.log

# Check verification success rate
grep "Status:" /var/log/ecommerce/backup-verification/*.log | tail -10
```

## Recovery Time Objectives (RTO/RPO)

| Component | RTO | RPO | Backup Frequency |
|-----------|-----|-----|------------------|
| PostgreSQL (Main) | 30 min | 15 min | Every 6 hours |
| PostgreSQL (AI) | 30 min | 15 min | Every 6 hours |
| Redis Cache | 15 min | 1 hour | Daily |
| Media Files | 4 hours | 24 hours | Daily |

## Best Practices

### Before Running Backups

1. Ensure Docker daemon is running
2. Verify sufficient disk space: `df -h /backups`
3. Test AWS credentials: `aws s3 ls` (if using S3)
4. Check backup directory permissions: `ls -la /backups`

### Monitoring

```bash
# Check cron jobs are installed
sudo crontab -l
cat /etc/cron.d/ecommerce-backups

# Monitor backup execution
tail -f /var/log/ecommerce/backup.log

# Check backup sizes
du -sh /backups/*

# List recent backups
find /backups -name "*.sql.gz" -mtime -7 -ls
```

### Troubleshooting

**Issue: Backup verification fails**
```bash
# Check Docker is running
docker ps

# Check for test containers (should be cleaned up)
docker ps -a | grep test

# Manually cleanup test containers
docker stop $(docker ps -a | grep ecommerce_.*_test | awk '{print $1}')
docker rm $(docker ps -a | grep ecommerce_.*_test | awk '{print $1}')

# Run verification with verbose output
./verify-backup.sh --latest 2>&1 | tee verification-debug.log
```

**Issue: No backups found**
```bash
# Check backup directory structure
ls -R /backups/

# Check backup script is executable
ls -l scripts/backup/backup-databases.sh

# Check cron logs
grep CRON /var/log/syslog
```

**Issue: S3 upload fails**
```bash
# Test AWS credentials
aws s3 ls s3://ecommerce-backups-production/

# Check AWS CLI configuration
aws configure list

# Test S3 upload manually
aws s3 cp /backups/postgres/test.txt s3://ecommerce-backups-production/test.txt
```

## Security Considerations

1. **Encryption**: Use `--encrypt` flag for sensitive data
2. **Access Control**: Backup files contain sensitive data - restrict access
3. **Key Management**: Store GPG keys securely, separate from backups
4. **S3 Security**:
   - Enable bucket versioning
   - Enable server-side encryption
   - Use IAM roles with least privilege
   - Enable S3 bucket logging

## Compliance

This backup system supports compliance requirements for:
- **PCI-DSS**: Requires regular backup testing (weekly verification tests)
- **SOC 2**: Requires backup and recovery procedures (automated DR drills)
- **GDPR**: Supports data retention and deletion policies

## Support

For issues or questions:
1. Check logs: `/var/log/ecommerce/backup.log`
2. Review verification reports: `/var/log/ecommerce/backup-verification/`
3. Contact: Platform Team

## Related Documentation

- [Disaster Recovery Plan](../../docs/operations/disaster-recovery.md)
- [Backup Strategy](../../docs/operations/disaster-recovery.md#backup-strategy)
- [Recovery Testing](../../docs/operations/disaster-recovery.md#recovery-testing)
