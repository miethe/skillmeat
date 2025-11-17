# Consent Process Documentation

This document explains the legal consent process for publishing bundles on the SkillMeat marketplace, including what publishers consent to, how consent is recorded, and the legal implications.

## Table of Contents

- [Overview](#overview)
- [What Publishers Consent To](#what-publishers-consent-to)
- [Consent Recording Process](#consent-recording-process)
- [Legal Implications](#legal-implications)
- [Audit Trail](#audit-trail)
- [Consent Verification](#consent-verification)
- [Rights and Responsibilities](#rights-and-responsibilities)

## Overview

Before publishing a bundle to the SkillMeat marketplace, publishers must provide explicit consent to a compliance checklist. This ensures:

1. **Legal Compliance** - Publishers understand their obligations
2. **Transparency** - Clear record of what was agreed to
3. **Accountability** - Immutable audit trail for disputes
4. **Protection** - Both publishers and users are protected

The consent process uses cryptographic signatures to ensure integrity and non-repudiation.

## What Publishers Consent To

### Universal Consent Items

All publishers must consent to these items regardless of license:

1. **License Headers**
   - All files have appropriate license headers
   - SPDX identifiers are correct
   - Headers match declared license

2. **LICENSE File**
   - LICENSE file is present in bundle
   - LICENSE content matches declared license
   - LICENSE is complete and unmodified

3. **Copyright Notices**
   - Copyright notices are accurate
   - Copyright years are current
   - All copyright holders are properly credited

4. **Code Ownership**
   - No proprietary code included without permission
   - All code is legally redistributable
   - Rights to all included content verified

5. **Security**
   - No secrets or credentials in code
   - No API keys, passwords, or tokens
   - Sensitive data properly handled

6. **Attribution**
   - Attribution requirements understood
   - CREDITS file created (if needed)
   - Third-party licenses respected

### License-Specific Consent

#### For Permissive Licenses (MIT, Apache-2.0, BSD)

7. **License Preservation**
   - License text preserved in distributions
   - Copyright notices maintained
   - Attribution requirements met

#### For Apache-2.0 Specifically

8. **NOTICE File**
   - NOTICE file created if upstream requires it
   - Attributions properly formatted
   - Apache requirements understood

9. **Patent Grant**
   - Patent grant implications understood
   - No conflicting patent claims
   - Grant terms acceptable

#### For GPL/Copyleft Licenses

10. **Source Code**
    - Source code included or accessible
    - Complete source provided
    - Build instructions included

11. **Modifications**
    - Modifications clearly marked
    - Change log maintained
    - Original authors credited

12. **License Propagation**
    - Same license applied to derivatives
    - Copyleft requirements understood
    - No license conflicts

13. **Copyright Preservation**
    - Original copyright notices preserved
    - All license notices maintained
    - Authors properly credited

#### For Proprietary/Commercial Licenses

14. **Redistribution Permission**
    - Explicit written permission obtained
    - Permission scope clearly defined
    - Documentation provided

15. **Terms Clarity**
    - License agreement terms clear
    - All restrictions documented
    - Users understand limitations

16. **Commercial Use**
    - Commercial use explicitly allowed
    - Marketplace distribution permitted
    - Pricing/terms disclosed

## Consent Recording Process

### Step 1: Generate Checklist

```bash
# Generate license-specific checklist
skillmeat compliance-checklist my-bundle.zip --license MIT

# Output:
# Checklist ID: abc123-def456-ghi789
# Items: 8 (6 required)
# Checklist saved: ~/.skillmeat/compliance/abc123-def456-ghi789.json
```

The checklist is tailored to your bundle's license and stored locally.

### Step 2: Review Requirements

Review each checklist item carefully:

```
LICENSE:
* [X] All files have appropriate license headers
      Ensure every source file includes SPDX identifier

* [X] LICENSE file present and matches declared license
      Include complete license text in LICENSE file

ATTRIBUTION:
* [X] Attribution requirements understood and documented
      Know what attributions are required for dependencies
```

Items marked with `*` are required for publication.

### Step 3: Provide Consent

```bash
# Interactive consent collection
skillmeat compliance-consent <checklist-id> --publisher-email you@example.com

# For each required item:
# > All files have appropriate license headers
#   Ensure every source file includes SPDX identifier
# Do you confirm? [y/N]: y

# > LICENSE file present and matches declared license
#   Include complete license text in LICENSE file
# Do you confirm? [y/N]: y
```

### Step 4: Signature Generation

After collecting all consents, SkillMeat:

1. Creates canonical representation of your responses
2. Generates SHA-256 cryptographic signature
3. Records timestamp and publisher email
4. Stores immutable consent record

```
Consent recorded successfully!
  Consent ID: 9f8e7d6c-5b4a-3210-fedc-ba9876543210
  Signature: sha256:a1b2c3d4e5f6...
  Timestamp: 2024-01-15T10:30:00Z
```

### Step 5: Verification

The consent can be verified at any time:

```bash
# Verify consent integrity
skillmeat compliance-history --publisher you@example.com

# Shows:
# Date       Consent ID  Bundle ID    Items Complete
# 2024-01-15 9f8e7d6c    my-bundle    6     ✓
```

## Legal Implications

### Binding Agreement

By providing consent, you legally affirm that:

1. **Statements are True** - All checklist items you confirmed are accurate
2. **Rights Exist** - You have the rights to publish the bundle
3. **Compliance Met** - The bundle meets all legal requirements
4. **Responsibility Accepted** - You accept liability for inaccuracies

### Consequences of False Consent

Providing false or misleading consent can result in:

- **Bundle Rejection** - Immediate removal from marketplace
- **Account Suspension** - Temporary or permanent ban
- **Legal Action** - Copyright holders may pursue legal remedies
- **Reputation Damage** - Public record of violations

### Consent Revocation

Consent cannot be revoked once published, but you can:

1. **Unpublish Bundle** - Remove from marketplace
2. **Update Bundle** - Publish corrected version with new consent
3. **Contact Support** - Request assistance for serious issues

## Audit Trail

### Immutable Log

All consents are stored in an append-only log:

```json
{
  "version": "1.0.0",
  "created": "2024-01-01T00:00:00Z",
  "consents": [
    {
      "consent_id": "9f8e7d6c-5b4a-3210-fedc-ba9876543210",
      "checklist_id": "abc123-def456-ghi789",
      "bundle_id": "my-bundle",
      "publisher_email": "you@example.com",
      "timestamp": "2024-01-15T10:30:00Z",
      "consents": {
        "files_licensed": true,
        "license_file": true,
        "copyright_accurate": true,
        "no_proprietary": true,
        "no_secrets": true,
        "attribution_understood": true
      },
      "signature": "sha256:a1b2c3d4e5f6...",
      "ip_address": "192.168.1.100"
    }
  ]
}
```

### Data Retention

Consent records are:

- **Permanent** - Never deleted
- **Immutable** - Cannot be modified after creation
- **Auditable** - Available for review and export
- **Cryptographically Signed** - Tamper-evident

### Access Controls

Consent records are:

- **Private** - Only visible to publisher and marketplace admins
- **Exportable** - Publishers can export their own records
- **Verifiable** - Signatures can be independently verified

## Consent Verification

### For Publishers

Verify your own consents:

```bash
# View your consent history
skillmeat compliance-history --publisher you@example.com

# Export specific consent
skillmeat compliance-consent export <consent-id> > consent.json

# Verify signature
skillmeat compliance-consent verify <consent-id>
```

### For Marketplace Admins

Admins can verify any consent:

```bash
# View all consents for bundle
GET /api/marketplace/compliance/history?bundle_id=my-bundle

# Verify consent signature
GET /api/marketplace/compliance/consent/<consent-id>/verify

# Export for legal review
GET /api/marketplace/compliance/consent/<consent-id>/export
```

### Signature Verification

Signatures can be independently verified:

1. Reconstruct canonical representation from consent data
2. Compute SHA-256 hash
3. Compare with stored signature
4. Match confirms integrity

```python
import hashlib
import json

# Canonical representation
data = {
    "consent_id": "...",
    "checklist_id": "...",
    "bundle_id": "...",
    "publisher_email": "...",
    "timestamp": "...",
    "consents": [sorted items]
}

# Generate signature
canonical = json.dumps(data, sort_keys=True)
signature = hashlib.sha256(canonical.encode()).hexdigest()

# Compare with stored signature
assert f"sha256:{signature}" == stored_signature
```

## Rights and Responsibilities

### Publisher Rights

As a publisher, you have the right to:

1. **Review Checklist** - See all requirements before consenting
2. **Decline** - Choose not to publish if requirements are unacceptable
3. **Update** - Publish updated versions with new consents
4. **Export** - Obtain copies of your consent records
5. **Support** - Request assistance with compliance questions

### Publisher Responsibilities

As a publisher, you are responsible for:

1. **Accuracy** - Ensuring all consents are truthful
2. **Compliance** - Meeting all legal requirements
3. **Maintenance** - Keeping bundles compliant over time
4. **Updates** - Promptly fixing compliance issues
5. **Transparency** - Being honest about bundle contents

### Marketplace Rights

The marketplace reserves the right to:

1. **Verify** - Check compliance independently
2. **Reject** - Refuse publication if requirements not met
3. **Remove** - Unpublish bundles violating terms
4. **Audit** - Review consent records for accuracy
5. **Report** - Disclose violations to copyright holders

### User Rights

Users of marketplace bundles have the right to:

1. **Transparency** - Know what licenses apply
2. **Attribution** - See proper credits
3. **Compliance** - Trust bundles meet legal requirements
4. **Reporting** - Flag compliance issues
5. **Access** - View compliance information

## Best Practices

### Before Consenting

1. **Review Thoroughly** - Read each checklist item carefully
2. **Verify Accuracy** - Double-check all statements
3. **Scan Bundle** - Use automated tools to verify compliance
4. **Seek Advice** - Consult legal counsel if uncertain
5. **Document** - Keep records of verification steps

### During Consent

1. **Be Honest** - Only consent to items that are true
2. **Ask Questions** - Seek clarification if needed
3. **Take Time** - Don't rush through the process
4. **Save Records** - Keep copies of consent IDs
5. **Verify Results** - Confirm consent was recorded correctly

### After Consenting

1. **Maintain Compliance** - Keep bundle compliant over time
2. **Update Promptly** - Fix issues as soon as discovered
3. **Track Changes** - Document updates and modifications
4. **Re-consent** - Provide new consent for significant changes
5. **Monitor** - Watch for user-reported issues

## Common Questions

### Q: Can I change my consent after publishing?

No. Consent records are immutable. If you need to make changes:
1. Unpublish the current bundle
2. Fix the issues
3. Provide new consent
4. Republish

### Q: What if I made a mistake in my consent?

Contact marketplace support immediately:
1. Explain the error
2. Unpublish the bundle if necessary
3. Correct the issues
4. Republish with accurate consent

### Q: How long are consent records kept?

Permanently. Consent records are never deleted to maintain audit trail integrity.

### Q: Can I consent on behalf of my organization?

Yes, if you have authority to do so. Include organization name in metadata:

```bash
skillmeat compliance-consent <id> \
  --publisher-email legal@company.com \
  --organization "Company Name"
```

### Q: What if I don't agree with a required item?

You cannot publish without consenting to all required items. Options:
1. Modify bundle to meet requirements
2. Choose different license with fewer requirements
3. Seek legal advice for alternative approaches
4. Don't publish to marketplace

## Getting Help

### Compliance Support

```bash
# Scan for compliance issues
skillmeat compliance-scan bundle.zip

# Generate checklist
skillmeat compliance-checklist bundle.zip

# View consent history
skillmeat compliance-history --publisher you@example.com
```

### Legal Questions

For legal questions about consent or compliance:
- Consult with a qualified attorney
- Review license documentation
- Contact marketplace support
- Seek community guidance

### Technical Issues

For technical issues with consent process:
- Check SkillMeat documentation
- Review error messages carefully
- Contact technical support
- Report bugs on GitHub

## Disclaimer

This documentation provides information about the SkillMeat consent process but is not legal advice. Publishers are solely responsible for ensuring their bundles comply with all applicable laws and licenses. Consult a qualified attorney for specific legal questions.

## Resources

- [Legal Compliance Guide](./compliance-guide.md)
- [Attribution Requirements](./attribution-requirements.md)
- [SkillMeat Terms of Service](https://skillmeat.io/terms)
- [Marketplace Publisher Agreement](https://skillmeat.io/publisher-agreement)
