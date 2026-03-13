---
name: data-handling-policy
description: PII classification, encryption, retention, and cross-border transfer policy
entity_type: context_file
category: data-governance
auto_load: true
project: "{{PROJECT_NAME}}"
author: "{{AUTHOR}}"
date: "{{DATE}}"
references:
  - "NIST SP 800-122 — Guide to Protecting PII"
  - "GDPR Articles 5, 17, 25, 44-49"
  - "CCPA / CPRA — California Consumer Privacy Act"
  - "PCI-DSS v4.0 Requirement 3 — Protect Stored Account Data"
---

# Data Handling Policy — {{PROJECT_NAME}}

Governs how all data is classified, stored, transmitted, masked, and purged within
this project. Engineers must apply the correct classification tier to every field
in every data model.

## Data Classification Tiers

| Tier | Label | Examples | Default Controls |
|------|-------|----------|-----------------|
| 1 | **Public** | Product names, published rates | No restrictions |
| 2 | **Internal** | Internal IDs, non-PII audit metadata | Access controls, no external exposure |
| 3 | **Confidential** | Name, email, phone, transaction amounts | Encrypted at rest, access logging |
| 4 | **Restricted** | SSN, PAN, account numbers, government IDs | Field-level encryption, strict access, MFA required |

All Tier 4 fields must be annotated in ORM models:

```python
from sqlalchemy import String
from skillmeat_fsc.data import restricted_field  # project annotation helper

class Customer(Base):
    ssn_encrypted = restricted_field(String(512), label="SSN")
    pan_token = restricted_field(String(64), label="card_token")
```

## PII Identification and Handling Rules

The following field types constitute PII under GLBA and GDPR and must be treated
as Tier 3 (Confidential) at minimum:

- Full legal name (first + last)
- Date of birth
- Email address
- Phone number
- Physical address
- IP address (when linked to an individual)
- Device identifiers when linked to an individual

The following constitute **Sensitive PII** (Tier 4 / Restricted):

- Social Security Number (SSN) / Tax ID (TIN / EIN)
- Passport / government-issued ID numbers
- Full card PAN, card expiry, CVV
- Bank account numbers and routing numbers
- Biometric data

## Encryption Requirements

### At Rest

- **AES-256-GCM** for all Tier 4 fields (field-level encryption via approved KMS).
- Key hierarchy: data encryption key (DEK) per tenant, wrapped by key encryption
  key (KEK) stored in HSM-backed KMS.
- Key rotation: DEKs rotated annually; KEKs rotated every 3 years or on compromise.
- Encrypted field format (in database column): `v1$<base64-iv>$<base64-ciphertext>$<base64-tag>`
- Database-level encryption (TDE) is required in addition to field-level encryption
  for Tier 3 and Tier 4 data stores.

### In Transit

- **TLS 1.2 minimum**; TLS 1.3 preferred for all new services.
- Cipher suite whitelist: `TLS_AES_256_GCM_SHA384`, `TLS_CHACHA20_POLY1305_SHA256`,
  `ECDHE-RSA-AES256-GCM-SHA384`. Disable RC4, 3DES, and export ciphers.
- Certificate pinning required for mobile clients communicating with payment APIs.
- Internal service mesh communication: mTLS enforced at the sidecar / service mesh
  layer.

## Data Retention and Purging Policies

| Data Type | Retention Period | Purge Method |
|-----------|-----------------|--------------|
| Transaction records | 7 years (SOX / BSA) | Cryptographic shredding |
| Audit logs | 7 years | Append-only store; deletion prohibited |
| Customer PII (active) | Duration of relationship + 5 years | Soft-delete, then hard purge |
| Customer PII (prospective) | 2 years from last interaction | Hard purge |
| Authentication logs | 1 year | Hard purge after archival |
| CVC / CVV | Never stored | N/A |

Automated purge jobs must log a purge event to the audit trail with record count
and initiating job ID. Manual purges require compliance approval.

## Masking Patterns for Display

Apply these masks whenever PII is displayed in UI, logs, or API responses:

```python
def mask_ssn(ssn: str) -> str:
    return f"***-**-{ssn[-4:]}"          # ***-**-1234

def mask_pan(pan: str) -> str:
    return f"{'*' * 12}{pan[-4:]}"        # ************1234

def mask_account(account: str) -> str:
    return f"****{account[-4:]}"          # ****6789

def mask_email(email: str) -> str:
    local, domain = email.split('@', 1)
    return f"{local[:2]}{'*' * (len(local) - 2)}@{domain}"  # jo***@example.com
```

Never store masked values — always mask at read time in the presentation layer.

## Cross-Border Data Transfer Constraints

- **EU personal data** subject to GDPR may not leave the EEA without either:
  - Standard Contractual Clauses (SCCs) in place, or
  - Transfer Impact Assessment (TIA) completed and approved.
- **US financial data** subject to GLBA must remain within approved data center
  regions. Cross-region replication requires data residency review.
- Any new cloud region or third-party data processor must be reviewed by Legal
  and added to the ROPA (Record of Processing Activities) before go-live.
- Data localization requirements for the applicable jurisdiction must be verified
  before launching in a new country.

## Database Field-Level Encryption Pattern

```python
# Approved pattern: transparent encrypt/decrypt via SQLAlchemy TypeDecorator
from skillmeat_fsc.crypto import EncryptedType

class CustomerProfile(Base):
    __tablename__ = "customer_profiles"

    id = Column(UUID(as_uuid=True), primary_key=True)
    # Plaintext fields (Tier 2)
    customer_id = Column(String(36), nullable=False, index=True)
    # Encrypted fields (Tier 4) — transparent encrypt/decrypt
    ssn = Column(EncryptedType(String), nullable=True)
    account_number = Column(EncryptedType(String), nullable=True)
```

`EncryptedType` calls the approved KMS for DEK resolution on each access.
Bulk operations that bypass the ORM must explicitly call `crypto.encrypt()` /
`crypto.decrypt()` — raw SQL inserts into encrypted columns are prohibited.
