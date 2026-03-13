# Data Privacy Rules

Path scope: all files

These rules enforce data privacy requirements under GDPR, CCPA, and GLBA. They apply to
all code that processes, stores, transmits, or references personal information.

## PII Definition and Classification

**Tier 1 — Restricted PII** (highest protection, field-level encryption required):
- Social Security Numbers (SSNs) / Tax Identification Numbers
- Payment card PANs, CVVs, expiry dates
- Government-issued ID numbers (passport, driver's license)
- Bank account numbers and routing numbers
- Biometric data

**Tier 2 — Sensitive PII** (encrypted at rest, masked in logs):
- Full name + date of birth combination
- Precise geolocation (lat/lng to 4+ decimal places)
- Medical or financial condition indicators
- Authentication credentials (passwords, PINs, security answers)

**Tier 3 — Identifiable PII** (cannot be logged in plaintext, must be pseudonymized):
- Email addresses
- Phone numbers
- IP addresses linked to accounts
- Device fingerprints

## Invariants

1. **No PII in logs.** Log messages must never contain raw PII. Use masked/tokenized
   values: `user_id=<uuid>` not `email=user@example.com`. Violation is a P1 incident.

2. **No PII in error messages.** Exception messages, HTTP error responses, and stack
   traces must not contain PII. Use opaque identifiers only.

3. **No PII in URLs.** PII must not appear in URL path segments or query parameters —
   they are logged by proxies, CDNs, and browsers.

4. **Consent before collection.** New PII collection points must have a corresponding
   consent record or lawful basis documented in the data map. Consult compliance before
   adding new PII fields.

5. **Retention limits enforced in code.** PII must be deleted or anonymized per the
   retention schedule. Hard-delete logic must be tested; soft-delete alone is insufficient
   for GDPR erasure.

6. **Data minimization.** Collect only PII that is necessary for the stated purpose.
   Do not add PII fields "in case we need them later."

7. **Right-to-deletion support.** Any new PII storage must be registered in the
   data inventory and must support the erasure workflow.

## Cross-Border Transfer Controls

- EU/EEA personal data must not be transferred outside the region without an approved
  legal mechanism (SCCs, adequacy decision, or BCRs).
- Document the transfer mechanism in the service's data flow diagram before deployment.

## Third-Party Data Sharing

- PII shared with vendors must be covered by a signed DPA (Data Processing Agreement).
- Log the categories and legal basis for all third-party sharing.
- Never share Tier 1 PII with analytics or advertising platforms.

## Testing and Development

- Use synthetic PII generators for test data — never copy production records.
- Test environments must not have access to production PII databases.
- Anonymized production snapshots are acceptable only with approval and only after
  running the approved anonymization pipeline.
