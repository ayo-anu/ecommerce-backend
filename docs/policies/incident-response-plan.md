# Incident Response Plan

## Overview

This Incident Response Plan (IRP) defines the procedures for identifying, responding to, and recovering from security incidents affecting the E-Commerce Platform. The plan ensures rapid and effective response to minimize damage, reduce recovery time, and maintain compliance with regulatory requirements.

**Plan Owner**: Security Team
**Effective Date**: 2025-12-19
**Review Frequency**: Quarterly
**Testing Frequency**: Semi-annual
**Compliance**: PCI-DSS Requirement 12.10, SOC 2, GDPR Article 33

## Table of Contents

1. [Purpose](#purpose)
2. [Scope](#scope)
3. [Incident Classification](#incident-classification)
4. [Incident Response Team](#incident-response-team)
5. [Response Phases](#response-phases)
6. [Incident Types](#incident-types)
7. [Communication Plan](#communication-plan)
8. [Tools and Resources](#tools-and-resources)
9. [Post-Incident Activities](#post-incident-activities)
10. [Testing and Exercises](#testing-and-exercises)

---

## Purpose

The purpose of this plan is to:

1. **Minimize damage** from security incidents
2. **Reduce recovery time** and costs
3. **Maintain business continuity** during and after incidents
4. **Ensure compliance** with legal and regulatory requirements
5. **Preserve evidence** for investigation and legal proceedings
6. **Learn and improve** from incident experiences

---

## Scope

This plan applies to:

- **All security incidents** affecting the platform
- **All systems and data**: production, staging, development
- **All incident types**: cyberattacks, data breaches, system failures, insider threats
- **All personnel**: employees, contractors, third-party vendors
- **24/7 coverage**: incidents can occur at any time

---

## Incident Classification

### Severity Levels

| Level | Name | Description | Response Time | Escalation |
|-------|------|-------------|---------------|------------|
| **P0** | Critical | System down, data breach, active attack | < 15 minutes | Immediate, all hands |
| **P1** | High | Severe degradation, potential breach | < 1 hour | Security team + management |
| **P2** | Medium | Moderate impact, contained threat | < 4 hours | Security team |
| **P3** | Low | Minor impact, informational | < 24 hours | On-call engineer |

### Severity Assessment Criteria

#### P0 - Critical

- **Data Breach**: Confirmed or suspected cardholder data exposure
- **Active Attack**: Ongoing ransomware, DDoS, or intrusion
- **Complete Outage**: All production systems unavailable
- **Regulatory Impact**: Mandatory breach notification required
- **Financial Impact**: > $100,000 estimated loss

**Examples:**
- Database containing customer data accessed by unauthorized party
- Ransomware encrypting production systems
- Payment processing completely unavailable
- Full PAN exposure (if ever stored)

#### P1 - High

- **Suspicious Access**: Unauthorized access to sensitive systems
- **Partial Outage**: Critical service degraded or unavailable
- **Malware Detection**: Malware found in production environment
- **Significant Vulnerability**: Actively exploited critical CVE
- **Financial Impact**: $10,000 - $100,000 estimated loss

**Examples:**
- Admin account compromised
- API service unavailable for > 30 minutes
- Cryptominer detected in container
- Zero-day exploit affecting our stack

#### P2 - Medium

- **Security Alert**: Unusual activity detected
- **Minor Outage**: Non-critical service affected
- **Failed Attack**: Attack detected and blocked
- **Policy Violation**: Security policy breach
- **Financial Impact**: $1,000 - $10,000 estimated loss

**Examples:**
- Multiple failed login attempts from unknown IPs
- Search service degraded
- Phishing email sent to employees
- Unpatched vulnerability discovered

#### P3 - Low

- **Informational**: Security event with no immediate impact
- **False Positive**: Resolved security alert
- **Minor Violation**: Policy violation with no security impact
- **Financial Impact**: < $1,000 estimated loss

**Examples:**
- Automated security scan finding (non-exploitable)
- Employee accessing data for legitimate but unusual reason
- Certificate expiring in 30 days (automated renewal)

---

## Incident Response Team

### Core Team

| Role | Responsibilities | Contact |
|------|------------------|---------|
| **Incident Commander** | Overall incident coordination, decision-making | On-call rotation |
| **Security Lead** | Security analysis, threat assessment, remediation | security@example.com |
| **Technical Lead** | System recovery, technical implementation | devops@example.com |
| **Communications Lead** | Internal/external communications, PR | communications@example.com |
| **Legal Counsel** | Legal guidance, regulatory compliance | legal@example.com |
| **Executive Sponsor** | Strategic decisions, resource allocation | CTO/CISO |

### Extended Team (as needed)

- Database Administrator
- Network Engineer
- Application Developers
- Customer Support Manager
- HR (for insider threats)
- External Forensics (for major breaches)

### On-Call Schedule

**Primary On-Call:**
- Week 1: Security Engineer A
- Week 2: Security Engineer B
- Week 3: DevOps Engineer A
- Week 4: DevOps Engineer B

**Secondary On-Call:**
- Always: Security Team Lead
- Always: DevOps Team Lead

**Escalation Path:**
```
On-Call Engineer → Security Team Lead → CISO → CTO → CEO
```

---

## Response Phases

### Phase 1: Detection and Analysis (0-30 minutes)

#### 1.1 Detection

**Detection Sources:**
- Automated monitoring alerts (Prometheus, Grafana)
- Security scanning tools (Trivy, Snyk)
- User reports (customer support tickets)
- Anomaly detection (unusual traffic patterns)
- Log analysis
- Third-party notifications (Stripe, AWS)

**Initial Actions:**
```
1. Alert received (automated or manual)
2. On-call engineer acknowledges alert (< 5 min)
3. Perform initial triage
4. Create incident ticket
5. Activate incident response team (if needed)
```

#### 1.2 Initial Assessment

**Questions to Answer:**
- What is happening?
- When did it start?
- What systems are affected?
- Is it ongoing?
- What is the severity?
- Is customer data at risk?

**Documentation:**
```markdown
# Incident Report Template

**Incident ID**: INC-2025-001
**Severity**: P1
**Status**: Active
**Detected**: 2025-12-19 10:30 UTC
**Detected By**: Automated monitoring

## Summary
Brief description of the incident

## Impact
- Systems affected
- Customers affected
- Data at risk

## Timeline
- 10:30 - Alert triggered
- 10:32 - On-call acknowledged
- 10:35 - Incident commander assigned
```

#### 1.3 Initial Containment

**Immediate Actions:**
- Isolate affected systems (network segmentation)
- Revoke compromised credentials
- Enable additional logging
- Preserve evidence (snapshots, logs)
- Block malicious IPs/domains

**Example Commands:**
```bash
# Isolate compromised container
docker network disconnect ecommerce_backend compromised-container

# Revoke API key
vault write auth/token/revoke token=<compromised-token>

# Block IP at firewall
iptables -A INPUT -s <malicious-ip> -j DROP

# Take snapshot for forensics
docker commit compromised-container forensic-snapshot-$(date +%s)
```

### Phase 2: Containment, Eradication, and Recovery (1-24 hours)

#### 2.1 Short-term Containment

**Goals:**
- Stop the incident from spreading
- Minimize damage
- Maintain critical business operations

**Actions:**
- Implement firewall rules
- Disable compromised accounts
- Isolate affected network segments
- Implement rate limiting
- Deploy patches/hotfixes

#### 2.2 Evidence Collection

**Critical Evidence:**
- System logs (application, access, error)
- Network traffic captures
- Memory dumps
- Disk images
- Database snapshots
- Configuration files

**Evidence Chain of Custody:**
```bash
# Create forensic evidence package
mkdir -p /forensics/INC-2025-001/$(date +%Y%m%d_%H%M%S)
cd /forensics/INC-2025-001/$(date +%Y%m%d_%H%M%S)

# Collect logs
docker logs compromised-container > container.log 2>&1

# Collect system info
docker inspect compromised-container > container-inspect.json

# Create hash for integrity
sha256sum * > SHA256SUMS

# Sign evidence
gpg --sign SHA256SUMS
```

#### 2.3 Threat Analysis

**Determine:**
- Attack vector (how did they get in?)
- Attack timeline (when did it start?)
- Attacker capabilities (skill level, resources)
- Attack objectives (what did they want?)
- Data accessed (what was compromised?)

**Analysis Tools:**
- Log analysis (grep, awk, ELK)
- Network traffic analysis (Wireshark)
- Malware analysis (sandbox)
- Vulnerability scanning
- Threat intelligence feeds

#### 2.4 Eradication

**Remove Threat:**
- Remove malware
- Close attack vectors
- Patch vulnerabilities
- Strengthen security controls
- Update detection rules

**Verification:**
```bash
# Scan for malware
trivy rootfs --scanners vuln,secret,misconfig /

# Verify no backdoors
find / -name "*.php" -mtime -7 -exec grep -l "eval\|base64_decode" {} \;

# Check for persistence mechanisms
crontab -l
systemctl list-timers

# Verify user accounts
awk -F: '$3 >= 1000 {print $1}' /etc/passwd
```

#### 2.5 Recovery

**Restore Normal Operations:**
1. **Validate fixes** in staging environment
2. **Deploy patches** to production
3. **Restore from clean backups** (if needed)
4. **Verify system integrity**
5. **Gradually restore services**
6. **Monitor for recurrence**

**Recovery Checklist:**
- [ ] All malware removed
- [ ] Vulnerabilities patched
- [ ] Compromised credentials rotated
- [ ] System integrity verified
- [ ] Backups tested and verified
- [ ] Monitoring enhanced
- [ ] Services restored
- [ ] Performance verified

### Phase 3: Post-Incident Activity (1-7 days)

**Covered in detail in [Post-Incident Activities](#post-incident-activities) section**

---

## Incident Types

### 1. Data Breach

**Definition**: Unauthorized access to or disclosure of sensitive data

#### Response Procedures

**Immediate (0-1 hour):**
1. Identify scope of breach (what data, how many records)
2. Stop ongoing exfiltration
3. Preserve evidence
4. Activate legal and PR teams

**Short-term (1-24 hours):**
1. Contain breach (close access point)
2. Assess notification requirements
3. Begin forensic investigation
4. Prepare customer communication

**Medium-term (1-7 days):**
1. Notify affected parties (per legal requirements)
2. Notify regulators (if required)
3. Offer credit monitoring (if appropriate)
4. Complete forensic investigation

**Legal Notification Requirements:**

| Jurisdiction | Timeframe | Threshold |
|--------------|-----------|-----------|
| GDPR (EU) | 72 hours | Personal data breach |
| CCPA (California) | Without unreasonable delay | 500+ California residents |
| State laws (varies) | Varies by state | Varies |
| PCI-DSS | Immediately | Any cardholder data |

**Notification Template:**
```markdown
Subject: Security Incident Notification

Dear [Customer],

We are writing to inform you of a security incident that may have affected your personal information.

**What Happened:**
On [DATE], we discovered [BRIEF DESCRIPTION].

**Information Involved:**
The following information may have been accessed:
- [LIST DATA ELEMENTS]

**What We're Doing:**
- Immediately secured the affected systems
- Engaged cybersecurity experts
- Notified law enforcement
- Enhanced security measures

**What You Can Do:**
- Monitor your account statements
- Consider placing a fraud alert
- Change your password

**Contact:**
For questions: security@example.com or 1-800-XXX-XXXX

We sincerely apologize for this incident.

[COMPANY NAME]
```

### 2. Ransomware Attack

**Definition**: Malware that encrypts data and demands payment

#### Response Procedures

**DO NOT pay the ransom** (FBI recommendation)

**Immediate:**
1. Isolate infected systems (disconnect from network)
2. Identify ransomware variant
3. Check for available decryptors
4. Assess backup availability

**Containment:**
1. Shut down affected systems
2. Disable network shares
3. Block command & control servers
4. Scan all systems for infection

**Recovery:**
1. Restore from clean backups
2. Rebuild compromised systems
3. Patch vulnerabilities
4. Strengthen email filtering

**Prevention:**
- Regular offline backups
- Email security (anti-phishing)
- Endpoint protection
- User training

### 3. DDoS Attack

**Definition**: Distributed denial of service attack overwhelming systems

#### Response Procedures

**Immediate:**
1. Confirm it's a DDoS (not infrastructure failure)
2. Activate DDoS mitigation (Cloudflare, AWS Shield)
3. Identify attack type (volumetric, application-layer, protocol)

**Mitigation:**
1. Enable rate limiting
2. Block attack sources
3. Filter malicious traffic
4. Scale infrastructure (if volumetric)

**Communication:**
1. Status page update
2. Customer communication
3. Social media announcement

**Example Cloudflare Configuration:**
```yaml
# Enable "I'm Under Attack" mode
mode: under_attack

# Rate limiting
rate_limiting:
  threshold: 100 requests/minute
  action: challenge

# Bot management
bot_management:
  enabled: true
  mode: block
```

### 4. Compromised Credentials

**Definition**: User credentials obtained by attacker

#### Response Procedures

**Immediate:**
1. Disable compromised account
2. Revoke active sessions
3. Check for unauthorized access
4. Reset password

**Investigation:**
1. Review account activity logs
2. Identify data accessed
3. Determine compromise method
4. Check for lateral movement

**Remediation:**
1. Force password reset
2. Enable MFA
3. Notify account owner
4. Monitor for further compromise

**Prevention:**
- Mandatory MFA for all accounts
- Password complexity requirements
- Leaked credential monitoring
- Account lockout policies

### 5. Insider Threat

**Definition**: Malicious or negligent actions by employee/contractor

#### Response Procedures

**Immediate:**
1. Disable user access (all systems)
2. Preserve evidence (don't tip off employee)
3. Involve HR and Legal
4. Document all actions

**Investigation:**
1. Review audit logs (file access, emails, etc.)
2. Interview manager and colleagues
3. Forensic analysis of devices
4. Legal guidance on evidence collection

**Actions:**
1. Employment termination (if malicious)
2. Law enforcement notification (if criminal)
3. Civil proceedings (if appropriate)
4. Improve access controls

**Legal Considerations:**
- Employment law compliance
- Privacy rights
- Evidence admissibility
- Non-disclosure agreements

### 6. Supply Chain Attack

**Definition**: Attack through third-party vendor or dependency

#### Response Procedures

**Immediate:**
1. Identify compromised component
2. Assess our exposure
3. Disable/isolate affected systems
4. Check SBOM for affected services

**Investigation:**
1. Review vendor security
2. Scan for indicators of compromise
3. Check other vendor products
4. Industry coordination

**Remediation:**
1. Remove compromised component
2. Deploy patch/update
3. Audit vendor security
4. Enhance vendor risk management

**Example:**
```bash
# Check SBOM for vulnerable package
syft backend:latest -o json | jq '.artifacts[] | select(.name=="log4j")'

# Scan for exploitation attempts
grep -r "jndi:ldap" /var/log/

# Update to patched version
# Update requirements.txt and redeploy
```

---

## Communication Plan

### Internal Communication

**Incident Slack Channel:**
- Create dedicated channel: `#incident-[ID]-[short-description]`
- Add response team members
- Post updates every 30 minutes (P0/P1)
- Use for coordination only

**Status Page:**
- Update: https://status.example.com
- Use standard messaging templates
- Update every 30 minutes during active incident

**Executive Briefing:**
- P0: Immediate notification
- P1: Within 1 hour
- P2: Daily summary
- P3: Weekly summary

### External Communication

**Customer Communication:**

**When to Notify:**
- Service disruption > 30 minutes
- Data breach affecting customers
- Security incident with customer impact

**Channels:**
- Email (all affected customers)
- Status page (https://status.example.com)
- Social media (Twitter, LinkedIn)
- In-app notification

**Template:**
```
We're currently experiencing [ISSUE]. Our team is working to resolve this as quickly as possible.

Status: Investigating
Affected Services: [LIST]
Started: [TIME]

We'll provide updates every 30 minutes.

Latest update: [TIMESTAMP]
```

**Regulatory Notification:**

**PCI-DSS:**
- Notify payment brands immediately
- Notify acquiring bank
- Notify PCI forensic investigator (PFI)

**GDPR:**
- Notify supervisory authority within 72 hours
- Document reasoning if delay

**State Breach Laws:**
- Varies by state (typically "without unreasonable delay")
- Attorney General notification (some states)

### Media Relations

**Spokesperson:**
- Only designated PR team members
- All media inquiries → PR team

**Holding Statement:**
```
We are aware of [INCIDENT] and are investigating. The security of our customers is our top priority. We will provide updates as we learn more.
```

---

## Tools and Resources

### Incident Management Tools

| Tool | Purpose | Access |
|------|---------|--------|
| **PagerDuty** | Incident alerting, on-call management | https://company.pagerduty.com |
| **Slack** | Team communication, incident channels | #security-incidents |
| **Jira** | Incident tracking, task management | Security project |
| **Confluence** | Documentation, runbooks | Incident Response space |
| **Zoom** | Incident war room (video calls) | security-war-room |

### Security Tools

| Tool | Purpose | Usage |
|------|---------|-------|
| **Vault Audit Logs** | Access logging | Review secret access |
| **Prometheus/Grafana** | Metrics, alerting | System monitoring |
| **Trivy** | Vulnerability scanning | Scan images |
| **Wireshark** | Network analysis | Packet capture |
| **Docker logs** | Container logs | `docker logs <container>` |

### External Resources

| Resource | Contact | Purpose |
|----------|---------|---------|
| **Stripe Security** | security@stripe.com | Payment incidents |
| **AWS Security** | AWS Support | Cloud infrastructure |
| **FBI Cyber Division** | (855) 292-3937 | Cybercrime reporting |
| **Law Enforcement** | Local PD cybercrime unit | Criminal investigation |
| **Forensics Firm** | [Contracted firm] | Major incident investigation |

### Runbooks

Location: `docs/operations/runbooks/`

- `incident-response.md` - This document
- `data-breach-response.md` - Data breach specifics
- `ransomware-response.md` - Ransomware specifics
- `ddos-mitigation.md` - DDoS response
- `system-compromise.md` - Compromised system response

---

## Post-Incident Activities

### Lessons Learned Meeting

**When**: Within 7 days of incident closure

**Attendees:**
- Incident response team
- Affected service owners
- Management (for P0/P1)

**Agenda:**
1. Incident timeline review
2. What went well?
3. What could be improved?
4. Action items

**Template:**
```markdown
# Lessons Learned: INC-2025-001

**Date**: 2025-12-26
**Incident**: Database compromise attempt
**Severity**: P1
**Duration**: 4 hours
**Attendees**: [List]

## Timeline
[Detailed timeline]

## What Went Well
- Detection within 5 minutes
- Rapid containment
- Good team coordination

## What Could Be Improved
- Backup restoration took too long
- Unclear escalation path
- Insufficient monitoring of X

## Action Items
1. [Action] - Owner: [Person] - Due: [Date]
2. [Action] - Owner: [Person] - Due: [Date]

## Root Cause
[Technical root cause analysis]

## Preventive Measures
[How to prevent recurrence]
```

### Incident Report

**Required for**: All P0/P1 incidents, data breaches

**Format**: Formal written report

**Distribution**: Executive team, board (for major incidents)

**Contents:**
- Executive summary
- Incident details
- Response actions
- Impact assessment
- Root cause analysis
- Remediation actions
- Lessons learned
- Recommendations

### Follow-up Actions

**Track in Jira:**
- Create tickets for all action items
- Assign owners
- Set deadlines
- Track to completion

**Categories:**
- Technical fixes (patch, configuration)
- Process improvements (update runbooks)
- Policy updates (change policies)
- Training (educate team)

---

## Testing and Exercises

### Tabletop Exercises

**Frequency**: Quarterly

**Format**: Discussion-based scenario

**Participants**: Incident response team

**Scenarios:**
- Q1: Ransomware attack
- Q2: Data breach (cardholder data)
- Q3: Insider threat
- Q4: Supply chain compromise

**Duration**: 2-3 hours

**Deliverables:**
- Exercise report
- Action items
- Plan updates

### Simulations

**Frequency**: Semi-annual

**Format**: Hands-on technical exercise

**Scope**: Realistic attack scenario

**Examples:**
- Red team penetration test
- Blue team detection/response
- Full incident response drill

### Plan Updates

**Triggers for Update:**
- After major incident
- After testing/exercises
- Organizational changes
- Technology changes
- Quarterly review

**Review Checklist:**
- [ ] Contact information current
- [ ] Escalation paths valid
- [ ] Tools/systems up to date
- [ ] Regulatory requirements current
- [ ] Lessons learned incorporated

---

## Compliance Checklist

### PCI-DSS Requirement 12.10

- [x] Incident response plan documented
- [x] Roles and responsibilities defined
- [x] Business continuity procedures included
- [x] Communication strategy defined
- [x] Testing performed annually
- [x] Plan updated based on testing
- [x] 24/7 availability ensured
- [x] Training provided to team

### GDPR Article 33

- [x] 72-hour notification procedure defined
- [x] Data breach notification template created
- [x] Supervisory authority contact documented
- [x] Documentation requirements outlined

### SOC 2 CC7.4

- [x] Incident response plan established
- [x] Incident classification defined
- [x] Response procedures documented
- [x] Testing performed
- [x] Improvements implemented

---

## Appendices

### Appendix A: Contact List

**Emergency Contacts**

| Name | Role | Phone | Email |
|------|------|-------|-------|
| John Doe | Security Lead | +1-555-0101 | john@example.com |
| Jane Smith | DevOps Lead | +1-555-0102 | jane@example.com |
| Bob Johnson | CTO | +1-555-0103 | bob@example.com |

**Vendor Contacts**

| Vendor | Contact | Phone | Email |
|--------|---------|-------|-------|
| Stripe | Security Team | Support portal | security@stripe.com |
| AWS | Support | Support portal | N/A |
| Legal Counsel | External firm | +1-555-0201 | legal@lawfirm.com |

### Appendix B: Incident Severity Matrix

[Quick reference chart for severity determination]

### Appendix C: Communication Templates

[Templates for various notifications]

### Appendix D: Legal and Regulatory Requirements

[Summary of notification requirements by jurisdiction]

---

**Document Version**: 1.0
**Last Updated**: 2025-12-19
**Next Review**: 2026-03-19 (Quarterly)
**Last Tested**: Not yet tested
**Next Test**: 2026-01-19
**Approved By**: CISO, CTO, Legal
