# {{PROJECT_NAME}} — Financial Services Project Configuration

> Generated: {{DATE}} | Author: {{AUTHOR}}
> Compliance Classification: **RESTRICTED** — Financial Services Production System

## Regulatory Framework

This project operates under the following regulatory obligations. All AI-assisted
development must respect these constraints without exception.

| Framework | Scope | Key Obligation |
|-----------|-------|----------------|
| **PCI-DSS v4.0** | Payment card data | Tokenization, no PAN in logs, encrypted transmission |
| **SOX** | Financial reporting systems | Audit trails, change management, segregation of duties |
| **BSA / AML** | Transaction processing | Transaction monitoring, SAR/CTR filing triggers |
| **GLBA** | Customer data | Privacy notices, data protection program, vendor management |
| **GDPR / CCPA** | EU/CA customer PII | Consent, right-to-deletion, cross-border transfer controls |

## Architecture Constraints

The following constraints are **non-negotiable** for this codebase:

1. **Audit logging is mandatory** for all state-changing operations. Every create,
   update, and delete must emit a structured audit event with actor, timestamp,
   resource, and before/after state.

2. **No plaintext PII at rest.** SSNs, account numbers, card PANs, and government
   IDs must be encrypted at field level (AES-256-GCM) before persistence.

3. **All secrets from vault.** API keys, database credentials, and signing keys must
   be sourced from the approved secrets manager. Hardcoded credentials trigger an
   immediate security incident.

4. **Tokenization for card data.** PANs must be tokenized at point of entry via the
   approved tokenization service. Raw PANs must never traverse application layers.

5. **TLS 1.2+ for all external communication.** Plaintext HTTP is prohibited for any
   external-facing or service-to-service communication.

## AI-Assisted Development Security Invariants

When using Claude Code or any AI assistant on this codebase:

- Do not include real customer data, PAN samples, or live credentials in prompts
- Generated code handling financial data must be reviewed by a human engineer
  before merge — AI-generated financial logic is never auto-merged
- Suggested cryptographic implementations must be reviewed against approved
  algorithm list in `context/api-security-standards.md`
- Any generated migration touching PII fields requires compliance sign-off

## Context Files (Auto-Loaded)

The following context files inform AI behavior on this project:

- `context/api-security-standards.md` — PCI-DSS compliant API patterns
- `context/data-handling-policy.md` — PII, encryption, and retention requirements
- `context/regulatory-compliance.md` — SOX, AML/KYC, BSA obligations

## Rules Files

Active enforcement rules for AI-assisted development:

- `rules/security.md` — Security invariants (authentication, secrets, audit logging)
- `rules/data-privacy.md` — PII handling and privacy enforcement rules

## Specs

- `specs/pre-deploy-compliance-checklist.md` — Required sign-offs before any
  production deployment

## Development Workflow Requirements

1. **Code Review**: All PRs require review by a qualified engineer. PRs touching
   payment processing, authentication, or PII fields require an additional
   compliance-aware reviewer.

2. **Compliance Sign-Off**: Changes to audit logging, encryption, or regulatory
   reporting logic require sign-off from the compliance team before merge.

3. **Dependency Scanning**: Run `pip audit` / `npm audit` before every release.
   Critical CVEs block deployment.

4. **Secrets Scanning**: Pre-commit hooks must include `detect-secrets` or
   equivalent. Failed scans block push.

5. **Test Coverage**: Financial calculation logic must maintain ≥ 95% branch
   coverage. Payment paths require integration tests against the sandbox environment.
