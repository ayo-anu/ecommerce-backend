# Access Control Matrix

## Document Information

**Organization:** E-Commerce Platform
**Document Type:** Access Control Policy
**Version:** 1.0
**Date:** 2025-12-19
**Classification:** Internal
**Review Frequency:** Quarterly
**Next Review:** 2026-03-19

---

## Table of Contents

1. [Overview](#overview)
2. [Access Control Principles](#access-control-principles)
3. [Role Definitions](#role-definitions)
4. [System Access Matrix](#system-access-matrix)
5. [Data Access Matrix](#data-access-matrix)
6. [Access Provisioning](#access-provisioning)
7. [Access Review](#access-review)

---

## Overview

### Purpose

This document defines the access control framework for the E-Commerce Platform, specifying:
- User roles and responsibilities
- Access levels for systems and data
- Provisioning and deprovisioning procedures
- Access review process

### Scope

**In Scope:**
- Production systems
- Staging/development environments
- Administrative interfaces
- Database access
- Cloud infrastructure
- Source code repositories
- Security tools (Vault, monitoring)

**Out of Scope:**
- End-user customer access (managed by application authentication)

### Principles

1. **Least Privilege** - Users granted minimum access required for job function
2. **Separation of Duties** - Critical functions require multiple people
3. **Need-to-Know** - Access based on business need
4. **Default Deny** - No access unless explicitly granted
5. **Role-Based** - Access determined by role, not individual
6. **Time-Limited** - Privileged access time-limited when possible

---

## Access Control Principles

### Authentication

**Requirements:**
- Unique user accounts (no shared accounts)
- Strong passwords (min 12 characters, complexity)
- Multi-factor authentication (MFA) for admin access (Q1 2026)
- SSH key-based authentication for infrastructure
- JWT tokens for API access

**Session Management:**
- Idle timeout: 15 minutes
- Absolute timeout: 8 hours
- Automatic logout on browser close
- Session invalidation on logout

### Authorization

**Method:** Role-Based Access Control (RBAC)

**Enforcement:**
- Django permissions and groups
- GitHub teams
- Cloud IAM policies
- Database roles
- API Gateway policies

---

## Role Definitions

### User Roles

#### 1. Developer (Standard)

**Job Function:** Software development, feature implementation, bug fixes

**Responsibilities:**
- Write and review code
- Create pull requests
- Run tests in development environment
- Participate in on-call rotation

**Access Level:** Limited

**Typical Team Members:**
- Junior Developer
- Mid-level Developer
- Frontend Developer
- Backend Developer

---

#### 2. Senior Developer

**Job Function:** Advanced development, architecture decisions, code reviews

**Responsibilities:**
- Complex feature development
- Architecture design
- Code review and approval
- Mentoring junior developers
- Limited production access (read-only)

**Access Level:** Standard

**Typical Team Members:**
- Senior Software Engineer
- Staff Engineer
- Tech Lead

---

#### 3. DevOps / SRE

**Job Function:** Infrastructure management, deployment, monitoring, incident response

**Responsibilities:**
- Manage infrastructure and deployment
- Monitor system health
- Respond to incidents
- Manage backups and disaster recovery
- Performance optimization

**Access Level:** Elevated

**Typical Team Members:**
- DevOps Engineer
- Site Reliability Engineer
- Platform Engineer

---

#### 4. Security Engineer

**Job Function:** Security architecture, vulnerability management, incident response

**Responsibilities:**
- Security monitoring and alerting
- Vulnerability assessment and remediation
- Incident response (security)
- Security tool management
- Compliance support

**Access Level:** Elevated

**Typical Team Members:**
- Security Engineer
- Information Security Analyst

---

#### 5. Data Analyst

**Job Function:** Business intelligence, analytics, reporting

**Responsibilities:**
- Data analysis and reporting
- Dashboard creation
- Query development
- Data quality monitoring

**Access Level:** Read-only (data)

**Typical Team Members:**
- Data Analyst
- Business Analyst
- Product Analyst

---

#### 6. Database Administrator (DBA)

**Job Function:** Database management, performance tuning, backup management

**Responsibilities:**
- Database performance optimization
- Query optimization
- Backup verification
- Database schema changes
- Access management

**Access Level:** Elevated (database)

**Typical Team Members:**
- Database Administrator
- Data Engineer

---

#### 7. Engineering Manager / CTO

**Job Function:** Technical leadership, strategic planning, team management

**Responsibilities:**
- Technical strategy
- Architecture oversight
- Resource allocation
- Risk management
- Approval authority

**Access Level:** Administrative

**Typical Team Members:**
- Engineering Manager
- CTO
- VP of Engineering

---

#### 8. Customer Support

**Job Function:** Customer assistance, order management, issue resolution

**Responsibilities:**
- Handle customer inquiries
- Process returns and refunds
- Order management
- Customer data lookup

**Access Level:** Limited (customer data)

**Typical Team Members:**
- Customer Support Representative
- Customer Success Manager

---

#### 9. System Administrator (Break-Glass)

**Job Function:** Emergency access for critical incidents

**Responsibilities:**
- Emergency system recovery
- Critical incident response
- Break-glass access only

**Access Level:** Privileged (temporary)

**Typical Team Members:**
- Designated senior engineers
- On-call personnel (during incidents)

---

## System Access Matrix

### Production Systems

| System/Resource | Developer | Senior Dev | DevOps/SRE | Security | DBA | Manager/CTO | Support |
|-----------------|-----------|------------|------------|----------|-----|-------------|---------|
| **Backend API** | | | | | | | |
| - Read (logs, metrics) | ❌ | ✅ | ✅ | ✅ | ✅ | ✅ | ❌ |
| - Write (config) | ❌ | ❌ | ✅ | ✅ | ❌ | ✅ | ❌ |
| - Restart services | ❌ | ❌ | ✅ | ❌ | ❌ | ✅ | ❌ |
| **Database (PostgreSQL)** | | | | | | | |
| - Read-only queries | ❌ | ✅ | ✅ | ✅ | ✅ | ✅ | ❌ |
| - Read PII/customer data | ❌ | ❌ | ❌ | ✅ | ✅ | ❌ | ✅ (limited) |
| - Write (DML) | ❌ | ❌ | ❌ | ❌ | ✅ | ❌ | ❌ |
| - Schema changes (DDL) | ❌ | ❌ | ❌ | ❌ | ✅ | ✅ | ❌ |
| - Backup management | ❌ | ❌ | ✅ | ❌ | ✅ | ✅ | ❌ |
| **Redis Cache** | | | | | | | |
| - Read | ❌ | ✅ | ✅ | ✅ | ✅ | ✅ | ❌ |
| - Write/Flush | ❌ | ❌ | ✅ | ❌ | ✅ | ✅ | ❌ |
| **HashiCorp Vault** | | | | | | | |
| - Read secrets (app) | ❌ | ❌ | ✅ | ✅ | ❌ | ✅ | ❌ |
| - Write/update secrets | ❌ | ❌ | ✅ | ✅ | ❌ | ✅ | ❌ |
| - Vault administration | ❌ | ❌ | ✅ | ✅ | ❌ | ✅ | ❌ |
| - Audit log access | ❌ | ❌ | ✅ | ✅ | ❌ | ✅ | ❌ |
| **Monitoring (Prometheus/Grafana)** | | | | | | | |
| - View dashboards | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ❌ |
| - Edit dashboards | ❌ | ✅ | ✅ | ✅ | ❌ | ✅ | ❌ |
| - Manage alerts | ❌ | ❌ | ✅ | ✅ | ❌ | ✅ | ❌ |
| **Infrastructure (Cloud Console)** | | | | | | | |
| - View resources | ❌ | ✅ | ✅ | ✅ | ❌ | ✅ | ❌ |
| - Create/modify resources | ❌ | ❌ | ✅ | ❌ | ❌ | ✅ | ❌ |
| - Delete resources | ❌ | ❌ | ✅ (approval) | ❌ | ❌ | ✅ | ❌ |
| - Billing access | ❌ | ❌ | ❌ | ❌ | ❌ | ✅ | ❌ |
| **Admin Dashboard** | | | | | | | |
| - Read-only | ❌ | ✅ | ✅ | ✅ | ❌ | ✅ | ✅ |
| - Manage products | ❌ | ❌ | ❌ | ❌ | ❌ | ✅ | ✅ |
| - Manage orders | ❌ | ❌ | ❌ | ❌ | ❌ | ❌ | ✅ |
| - Manage users | ❌ | ❌ | ❌ | ✅ | ❌ | ✅ | ❌ |
| - System configuration | ❌ | ❌ | ✅ | ✅ | ❌ | ✅ | ❌ |
| **CI/CD (GitHub Actions)** | | | | | | | |
| - View workflows | ✅ | ✅ | ✅ | ✅ | ❌ | ✅ | ❌ |
| - Trigger workflows | ❌ | ✅ | ✅ | ✅ | ❌ | ✅ | ❌ |
| - Modify workflows | ❌ | ✅ | ✅ | ✅ | ❌ | ✅ | ❌ |
| - Manage secrets | ❌ | ❌ | ✅ | ✅ | ❌ | ✅ | ❌ |
| **Servers (SSH Access)** | | | | | | | |
| - SSH access (jump host) | ❌ | ❌ | ✅ | ✅ | ❌ | ✅ | ❌ |
| - Root/sudo access | ❌ | ❌ | ✅ (limited) | ❌ | ❌ | ✅ | ❌ |

**Legend:**
- ✅ = Access granted
- ❌ = No access
- ✅ (approval) = Requires approval
- ✅ (limited) = Limited/restricted access

---

### Development & Staging Environments

| System/Resource | Developer | Senior Dev | DevOps/SRE | Security | DBA | Manager/CTO |
|-----------------|-----------|------------|------------|----------|-----|-------------|
| **Staging Environment** | | | | | | |
| - Deploy to staging | ❌ | ✅ | ✅ | ✅ | ❌ | ✅ |
| - Read logs | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ |
| - Database access | ✅ (read) | ✅ | ✅ | ✅ | ✅ | ✅ |
| - Configuration changes | ❌ | ✅ | ✅ | ✅ | ❌ | ✅ |
| **Development Environment** | | | | | | |
| - All access | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ |
| **Local Development** | | | | | | |
| - Docker Compose | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ |
| - Mock services | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ |

---

### Source Code & Version Control

| Resource | Developer | Senior Dev | DevOps/SRE | Security | DBA | Manager/CTO |
|----------|-----------|------------|------------|----------|-----|-------------|
| **GitHub Repository** | | | | | | |
| - Read source code | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ |
| - Create branches | ✅ | ✅ | ✅ | ✅ | ❌ | ✅ |
| - Create pull requests | ✅ | ✅ | ✅ | ✅ | ❌ | ✅ |
| - Approve pull requests | ❌ | ✅ | ✅ | ✅ | ❌ | ✅ |
| - Merge to main | ❌ | ✅ | ✅ | ✅ | ❌ | ✅ |
| - Force push to main | ❌ | ❌ | ❌ | ❌ | ❌ | ❌ (blocked) |
| - Manage repository settings | ❌ | ❌ | ✅ | ✅ | ❌ | ✅ |
| - Manage branch protection | ❌ | ❌ | ✅ | ✅ | ❌ | ✅ |
| **CODEOWNERS** | | | | | | |
| - services/backend/* | ❌ | ✅ | ✅ | ✅ | ❌ | ✅ |
| - services/ai/* | ❌ | ✅ | ✅ | ❌ | ❌ | ✅ |
| - deploy/* | ❌ | ❌ | ✅ | ✅ | ❌ | ✅ |
| - .github/workflows/* | ❌ | ❌ | ✅ | ✅ | ❌ | ✅ |
| - docs/security/* | ❌ | ❌ | ❌ | ✅ | ❌ | ✅ |

---

## Data Access Matrix

### Customer Data

| Data Type | Developer | Senior Dev | DevOps/SRE | Security | DBA | Manager/CTO | Support |
|-----------|-----------|------------|------------|----------|-----|-------------|---------|
| **PII (Personal Identifiable Information)** | | | | | | | |
| - Customer names | ❌ | ❌ | ❌ | ✅ (audit) | ✅ (need) | ❌ | ✅ |
| - Email addresses | ❌ | ❌ | ❌ | ✅ (audit) | ✅ (need) | ❌ | ✅ |
| - Phone numbers | ❌ | ❌ | ❌ | ✅ (audit) | ✅ (need) | ❌ | ✅ |
| - Shipping addresses | ❌ | ❌ | ❌ | ✅ (audit) | ✅ (need) | ❌ | ✅ |
| - IP addresses (logs) | ❌ | ✅ | ✅ | ✅ | ✅ | ✅ | ❌ |
| **Financial Data** | | | | | | | |
| - Order amounts | ❌ | ✅ (aggregate) | ✅ (aggregate) | ✅ | ✅ | ✅ | ✅ |
| - Payment tokens | ❌ | ❌ | ❌ | ❌ | ✅ (need) | ❌ | ❌ |
| - Last 4 digits (card) | ❌ | ❌ | ❌ | ✅ | ✅ | ❌ | ✅ |
| - Full payment details | ❌ | ❌ | ❌ | ❌ | ❌ (Stripe only) | ❌ | ❌ |
| **Behavioral Data** | | | | | | | |
| - Browsing history | ❌ | ✅ (aggregate) | ❌ | ✅ | ✅ | ✅ | ❌ |
| - Purchase history | ❌ | ✅ (aggregate) | ❌ | ✅ | ✅ | ✅ | ✅ |
| - Recommendations | ❌ | ✅ | ❌ | ❌ | ✅ | ✅ | ❌ |

**Access Restrictions:**
- All PII access must be logged and audited
- Customer Support: Can only access data for active support tickets
- DBA: Access only when required for database maintenance
- Security: Access for security investigations only
- Production data must not be copied to development environments

---

### Business Data

| Data Type | Developer | Senior Dev | DevOps/SRE | Security | DBA | Manager/CTO | Support |
|-----------|-----------|------------|------------|----------|-----|-------------|---------|
| **Product Catalog** | | | | | | | |
| - Product information | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ |
| - Pricing | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ |
| - Inventory levels | ❌ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ |
| **Business Metrics** | | | | | | | |
| - Revenue data | ❌ | ✅ (limited) | ✅ (limited) | ✅ | ✅ | ✅ | ❌ |
| - Conversion rates | ❌ | ✅ | ✅ | ✅ | ✅ | ✅ | ❌ |
| - Traffic analytics | ❌ | ✅ | ✅ | ✅ | ✅ | ✅ | ❌ |
| **Operational Data** | | | | | | | |
| - System logs (sanitized) | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ❌ |
| - Audit logs | ❌ | ❌ | ✅ | ✅ | ❌ | ✅ | ❌ |
| - Configuration data | ❌ | ✅ | ✅ | ✅ | ❌ | ✅ | ❌ |

---

### Secrets and Credentials

| Secret Type | Developer | Senior Dev | DevOps/SRE | Security | DBA | Manager/CTO |
|-------------|-----------|------------|------------|----------|-----|-------------|
| **Application Secrets** | | | | | | |
| - API keys (third-party) | ❌ | ❌ | ✅ | ✅ | ❌ | ✅ |
| - Database credentials | ❌ | ❌ | ✅ | ✅ | ✅ | ✅ |
| - Encryption keys | ❌ | ❌ | ✅ | ✅ | ❌ | ✅ |
| - JWT secrets | ❌ | ❌ | ✅ | ✅ | ❌ | ✅ |
| **Infrastructure Secrets** | | | | | | |
| - SSH keys | ❌ | ❌ | ✅ | ✅ | ❌ | ✅ |
| - Cloud credentials | ❌ | ❌ | ✅ | ❌ | ❌ | ✅ |
| - TLS certificates | ❌ | ❌ | ✅ | ✅ | ❌ | ✅ |
| **Vault Access** | | | | | | |
| - Read application secrets | ❌ | ❌ | ✅ | ✅ | ❌ | ✅ |
| - Write/rotate secrets | ❌ | ❌ | ✅ | ✅ | ❌ | ✅ |
| - Vault root token | ❌ | ❌ | ❌ | ✅ | ❌ | ✅ |

**Note:** All secrets stored in HashiCorp Vault. Access is logged and audited.

---

## Access Provisioning

### Access Request Process

1. **Request Submission**
   - Employee completes access request form
   - Specifies: System, access level, business justification
   - Submit via ticketing system (Jira/ServiceNow/email)

2. **Manager Approval**
   - Direct manager reviews and approves
   - Validates business need
   - Confirms appropriate role

3. **Security Review**
   - Security team reviews for compliance
   - Validates least privilege
   - Checks for conflicts of interest

4. **Provisioning**
   - DevOps/IT provisions access
   - Document in access log
   - Notify requester

5. **Verification**
   - Requester verifies access
   - Test access within 48 hours

**Timeline:**
- Standard access: Within 24 business hours
- Elevated access: Within 48 business hours
- Emergency access: Within 4 hours (with post-approval)

---

### New Hire Onboarding

**Day 1:**
- Create user accounts (email, GitHub, Slack)
- Provide onboarding documentation
- Security awareness briefing
- Sign acceptable use policy

**Week 1:**
- Provision role-based access
- Setup development environment
- Grant repository access
- Issue hardware/software

**Documentation:**
- Access provisioning checklist
- Onboarding guide
- Security policies acknowledgment

---

### Role Changes

**Process:**
1. Manager notifies HR and IT
2. Review new role requirements
3. Grant new access
4. Revoke old access (no longer needed)
5. Update access matrix
6. Confirm with employee

**Timeline:** Within 48 hours of role change

---

### Access Deprovisioning (Offboarding)

**Termination Checklist:**

**Immediate (Day 0):**
- Disable all user accounts
- Revoke VPN access
- Revoke SSH keys
- Revoke cloud console access
- Revoke Vault access
- Collect hardware (laptop, tokens)

**Within 24 hours:**
- Remove from GitHub teams
- Remove from Slack
- Remove from email distribution lists
- Remove from on-call schedule
- Delete/transfer data

**Within 1 week:**
- Rotate shared credentials (if applicable)
- Review audit logs for anomalies
- Archive user data
- Update documentation

**Documentation:**
- Offboarding checklist completed
- Manager sign-off
- IT/Security sign-off

---

## Access Review

### Quarterly Access Reviews

**Process:**
1. **Preparation** (Week 1)
   - Generate current access reports
   - Distribute to managers and system owners

2. **Review** (Week 2-3)
   - Managers review team member access
   - System owners review system access
   - Identify and document exceptions

3. **Remediation** (Week 3-4)
   - Revoke unnecessary access
   - Update access matrix
   - Document findings

4. **Reporting** (Week 4)
   - Summary report to management
   - Compliance report for audit
   - Action items tracked

**Scope:**
- All user accounts
- All system access
- All elevated privileges
- All third-party access

**Documentation:**
- Access review report
- Manager sign-offs
- Remediation log

---

### Privileged Access Review

**Frequency:** Monthly

**Scope:**
- Database administrator access
- Production server access (SSH)
- Vault administrator access
- Cloud infrastructure admin access
- GitHub repository admin access

**Process:**
- List all privileged accounts
- Verify business need
- Check for inactive accounts
- Review audit logs for suspicious activity
- Document review

---

### Automated Access Monitoring

**Daily:**
- Failed login attempts
- After-hours access
- Privileged command usage

**Weekly:**
- New accounts created
- Access changes
- Inactive accounts

**Monthly:**
- Orphaned accounts
- Accounts without recent use
- Privilege escalations

**Tools:**
- Vault audit logs
- GitHub audit log
- Cloud provider logs
- SIEM alerts (when implemented)

---

## Document Control

**Document Owner:** Security Team
**Reviewed By:** CTO, DevOps Lead
**Approved By:** CTO
**Distribution:** All employees, SOC 2 auditors

---

**Access Control Matrix - Version 1.0**
**Last Updated:** 2025-12-19
**Next Review:** 2026-03-19
