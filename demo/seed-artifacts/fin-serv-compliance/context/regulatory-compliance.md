---
name: regulatory-compliance
description: SOX, BSA/AML, KYC, and GLBA obligations for financial services development
entity_type: context_file
category: regulatory
auto_load: true
project: "{{PROJECT_NAME}}"
author: "{{AUTHOR}}"
date: "{{DATE}}"
references:
  - "Sarbanes-Oxley Act (SOX) Sections 302, 404"
  - "Bank Secrecy Act (BSA) / AML — 31 USC 5311-5332"
  - "FinCEN SAR/CTR Filing Requirements"
  - "Gramm-Leach-Bliley Act (GLBA) — 15 USC 6801-6809"
  - "USA PATRIOT Act Section 326 — CIP Requirements"
---

# Regulatory Compliance Reference — {{PROJECT_NAME}}

This document describes the regulatory obligations that govern software development,
data handling, and operational practices for this project. Engineers working on
features touching the areas below should review the relevant section before
implementation.

## SOX (Sarbanes-Oxley Act)

SOX applies to systems that support financial reporting, general ledger, accounts
payable/receivable, and any system of record that feeds financial statements.

### Change Management

- All production changes to SOX-in-scope systems require a change ticket with
  business justification, risk assessment, and rollback plan.
- Emergency changes must be retroactively documented within 24 hours.
- Code deployments must be traceable: every deployment record must reference the
  change ticket number and approved change window.

### Audit Trails

SOX-in-scope systems must maintain immutable audit trails with the following
attributes for every transaction and configuration change:

```
{
  "event_id": "<uuid>",
  "timestamp": "<ISO-8601 UTC>",
  "actor": "<user_id or service_account>",
  "action": "<CREATE|UPDATE|DELETE|READ>",
  "resource_type": "<entity name>",
  "resource_id": "<entity id>",
  "before_state": { ... } | null,
  "after_state": { ... } | null,
  "source_ip": "<ip>",
  "correlation_id": "<request_id>"
}
```

Audit logs must be stored in an append-only data store. Direct modification or
deletion of audit records is a SOX violation and must trigger an incident report.

### Segregation of Duties

- No single engineer may approve their own code change in SOX-in-scope repositories.
- Production access must be time-bound, require MFA, and generate an audit event.
- Developers may not have standing write access to production data stores.

## BSA / AML (Bank Secrecy Act / Anti-Money Laundering)

### Transaction Monitoring

Any system processing financial transactions must integrate with the approved
transaction monitoring service. Flag and route for review:

- Single transactions exceeding **$10,000 USD** equivalent (CTR threshold)
- Structuring indicators: multiple transactions below $10,000 that aggregate above
  the threshold within a rolling 24-hour window
- Transactions to/from OFAC-sanctioned entities or jurisdictions
- Unusual transaction velocity patterns (e.g., > 20 transactions in 1 hour)

### Suspicious Activity Reports (SAR)

SAR filing is required when there is a known, suspected, or identified criminal
violation involving $5,000 or more and the institution is involved in the
transaction. Filing timeline: **30 days** from detection (or 60 days if no
identified suspect).

SAR decision workflow must be documented in the case management system. Engineers
building SAR-adjacent features must coordinate with the BSA Officer.

### Currency Transaction Reports (CTR)

CTR must be filed for cash transactions exceeding $10,000 in a business day.
CTR filing is **mandatory** — there is no discretion. Automated CTR generation
must be tested against all edge cases: aggregate transactions, multiple accounts,
structured payments.

## KYC (Know Your Customer)

### Identity Verification Levels

| Level | Required For | Verification Method |
|-------|-------------|---------------------|
| Basic | Account opening | Name, DOB, address, SSN last-4 |
| Standard | Transaction limits > $5K/day | Government ID + liveness check |
| Enhanced | High-risk customers, PEPs | In-person or video KYC, source-of-funds |

### Document Requirements

- Government-issued photo ID (passport, driver's license, national ID)
- Proof of address (utility bill or bank statement, < 90 days old)
- For entities: certificate of incorporation, UBO (ultimate beneficial owner)
  declaration for any owner > 25% ownership stake

### Politically Exposed Persons (PEPs)

All customers must be screened against PEP databases at onboarding and on a
rolling basis (quarterly rescreening). PEP status triggers Enhanced Due Diligence
regardless of transaction volume.

## GLBA (Gramm-Leach-Bliley Act)

### Customer Data Protection

- Implement a written Information Security Program covering administrative,
  technical, and physical safeguards.
- All third-party service providers with access to customer financial data must
  have executed a Data Processing Agreement (DPA) with appropriate security
  representations.
- Annual risk assessments are required; findings must be remediated within agreed
  SLAs (Critical: 30 days, High: 90 days).

### Privacy Notices

- Initial privacy notice must be delivered at account opening.
- Annual privacy notice is required for all active customers.
- Opt-out rights must be honored within 30 days of customer election. Systems
  must enforce opt-out flags — no marketing communication to opted-out customers.

## Regulatory Reporting Requirements

| Report | Frequency | Deadline | Owner |
|--------|-----------|----------|-------|
| CTR (FinCEN 112) | Per transaction | Within 15 calendar days | BSA Officer |
| SAR (FinCEN 111) | Per investigation | Within 30-60 days | BSA Officer |
| FFIEC IT Examination | Annual | As scheduled | CISO |
| SOX 302/906 Certifications | Quarterly / Annual | 40 days after period end | CFO / CEO |
| GLBA Safeguards Annual Review | Annual | Q1 | Privacy Officer |

## Compliance Testing and Evidence Collection

Every release to production touching a regulated system must include:

1. **Test evidence**: Automated test results showing > 95% coverage of regulatory
   paths (CTR generation, SAR triggers, audit event emission).
2. **Static analysis**: No critical or high findings from SAST tools (Semgrep,
   Bandit, or equivalent).
3. **Penetration test**: For internet-facing endpoints modified in the release —
   tester attestation or exception with CISO sign-off.
4. **Change ticket**: Linked to deployment record, with approver signatures.
5. **Evidence archive**: All of the above retained in the compliance evidence store
   for a minimum of 7 years.
