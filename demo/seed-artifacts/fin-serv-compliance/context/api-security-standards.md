---
name: api-security-standards
description: PCI-DSS compliant API security patterns for financial services
entity_type: context_file
category: security
auto_load: true
project: "{{PROJECT_NAME}}"
author: "{{AUTHOR}}"
date: "{{DATE}}"
references:
  - "PCI-DSS v4.0 — https://www.pcisecuritystandards.org"
  - "OWASP API Security Top 10 — https://owasp.org/API-Security"
  - "NIST SP 800-63B — Digital Identity Guidelines"
---

# API Security Standards — {{PROJECT_NAME}}

Reference document for PCI-DSS v4.0 compliant API development in financial services
contexts. Apply these patterns to all new endpoints and during security reviews.

## Authentication Requirements

### External / User-Facing APIs

- **OAuth 2.0 with PKCE** is required for user-facing APIs. Implicit flow is
  prohibited.
- Access tokens: maximum 15-minute lifetime. Refresh tokens: 24-hour lifetime
  with sliding expiry, revocable.
- Token introspection endpoint must validate `aud`, `iss`, `exp`, and `nbf`
  claims. Any missing claim results in rejection.
- Session fixation protection: issue new session token on privilege escalation.

### Service-to-Service APIs

- **Mutual TLS (mTLS)** is required for all service-to-service communication
  inside the payment processing perimeter.
- Certificates must be issued by the internal PKI; self-signed certs are
  prohibited in staging and production.
- Certificate rotation must occur at least every 90 days. Rotation must be
  automated — manual rotation is an audit finding.
- Service identity must be validated against the approved service registry before
  processing any request.

## Input Validation Standards

Adopt a **reject-by-default** posture for all API inputs:

```python
# Approved pattern: strict schema validation at the boundary
from pydantic import BaseModel, validator, constr

class PaymentRequest(BaseModel):
    amount: Decimal  # Exact decimal — never float for monetary values
    currency: constr(regex=r'^[A-Z]{3}$')  # ISO 4217
    merchant_id: constr(regex=r'^[a-zA-Z0-9\-]{8,36}$')

    @validator('amount')
    def amount_must_be_positive(cls, v):
        if v <= 0:
            raise ValueError('amount must be positive')
        return v
```

- Reject requests with unexpected fields (`extra = 'forbid'` in Pydantic models).
- Validate content-type headers; reject `application/x-www-form-urlencoded` on
  JSON endpoints.
- Maximum request body size: 1 MB for standard endpoints, 10 MB for document
  upload endpoints only.
- All string inputs must have maximum length constraints explicitly defined.

## PCI-DSS Specific Patterns

### Card Data Tokenization

Raw PANs (Primary Account Numbers) must **never** traverse application layers.
Tokenize at the point of entry using the approved tokenization gateway:

```python
# CORRECT: Tokenize immediately, store token only
token = tokenization_service.tokenize(raw_pan)
payment_record.card_token = token

# WRONG: Never persist or pass raw PAN
payment_record.pan = raw_pan  # Security violation
```

- Card tokens must follow the format `tok_<environment>_<32-char-hex>`.
- Only the last four digits of a PAN may appear in any display, log, or export
  context.
- CVC/CVV must never be stored — not even transiently in application state.

### Log Sanitization

PAN, CVV, SSN, and account numbers must never appear in log output:

```python
# CORRECT: Mask before logging
logger.info("Payment processed", extra={"card": mask_pan(card_token)})

# WRONG: Raw values in logs
logger.info(f"Processing card {pan}")  # Audit violation
```

## Rate Limiting and DDoS Protection

- Authentication endpoints: **5 requests per minute** per IP. Lockout after 10
  failures in 15 minutes (exponential backoff required).
- Payment endpoints: **30 requests per minute** per authenticated user.
- Public endpoints (pricing, exchange rates): **100 requests per minute** per IP
  behind WAF.
- Implement token bucket algorithm; return `Retry-After` header on 429 responses.
- Distributed rate limit state must be stored in Redis (not in-process) to support
  horizontal scaling.

## Required Security Headers

All API responses must include the following headers:

```
Strict-Transport-Security: max-age=31536000; includeSubDomains; preload
Content-Security-Policy: default-src 'none'; frame-ancestors 'none'
X-Content-Type-Options: nosniff
X-Frame-Options: DENY
Referrer-Policy: no-referrer
Cache-Control: no-store
Permissions-Policy: geolocation=(), microphone=(), camera=()
```

- `X-Request-ID` must be echoed back in every response for correlation.
- Never expose server version information in headers (`Server`, `X-Powered-By`).

## API Versioning and Deprecation

Regulated APIs follow a mandatory deprecation lifecycle:

1. New version published with `v{N}` prefix: `/api/v2/payments`
2. Previous version enters **deprecated** state; `Deprecation` and `Sunset` headers
   added to all responses.
3. Minimum deprecation notice period: **6 months** for external APIs,
   **3 months** for internal APIs.
4. Sunset date requires compliance sign-off if the endpoint handles PCI or PII data.
5. Breaking changes without version bump are prohibited for regulated endpoints.
