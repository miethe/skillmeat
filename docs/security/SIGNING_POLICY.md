# SkillMeat Bundle Signing Policy

**Document Version:** 1.0
**Effective Date:** 2025-11-16
**Document Owner:** Security Team

---

## 1. Overview

This document defines the policies and procedures for cryptographic signing of SkillMeat bundles using Ed25519 digital signatures. Bundle signing provides:

- **Integrity:** Verify bundles haven't been tampered with
- **Authenticity:** Confirm the identity of the bundle creator
- **Non-repudiation:** Prove who created a bundle
- **Trust:** Establish chains of trust for bundle distribution

---

## 2. Signing Key Types

### 2.1 Private Signing Keys

**Purpose:** Sign bundles you create

**Storage:**
- **Primary:** OS keychain (macOS Keychain, Windows Credential Manager, Linux Secret Service)
- **Fallback:** Encrypted file storage (`~/.skillmeat/signing-keys/private/`)

**Protection:**
- Keys encrypted at rest
- Never transmitted over network
- Never logged or displayed
- Require user access to OS keychain or encrypted files

**Lifecycle:**
1. **Generation:** `skillmeat sign generate-key`
2. **Usage:** Automatic when creating bundles with `--sign` flag
3. **Backup:** Export public key for sharing
4. **Rotation:** Generate new key, revoke old key
5. **Revocation:** Delete private key with `skillmeat sign revoke`

---

### 2.2 Trusted Public Keys

**Purpose:** Verify bundles signed by others

**Storage:**
- **Primary:** OS keychain
- **Fallback:** Encrypted file storage (`~/.skillmeat/signing-keys/public/`)

**Trust Model:**
- Explicit trust required (import with `--trust` flag)
- Users must verify key fingerprints out-of-band
- Trust is all-or-nothing (no partial trust)
- Revoked keys immediately invalid

**Lifecycle:**
1. **Import:** `skillmeat sign import-key <public-key-file>`
2. **Verification:** Bundle signatures checked against trusted keys
3. **Trust Review:** Periodic review of trusted keys
4. **Revocation:** Remove trust with `skillmeat sign revoke`

---

## 3. Key Generation

### 3.1 Algorithm

**Ed25519 (EdDSA over Curve25519)**

**Why Ed25519:**
- Modern, secure signature algorithm
- Faster than RSA for signing and verification
- Smaller keys (32 bytes) and signatures (64 bytes)
- No known vulnerabilities
- Standardized in RFC 8032

**Key Properties:**
- Public key: 32 bytes (256 bits)
- Private key: 32 bytes (256 bits)
- Signature: 64 bytes (512 bits)
- Security level: ~128-bit (equivalent to RSA 3072-bit)

---

### 3.2 Key Generation Procedure

**Command:**
```bash
skillmeat sign generate-key --name "Your Name" --email "you@example.com"
```

**Process:**
1. Generate Ed25519 key pair using `cryptography` library
2. Compute SHA256 fingerprint of public key
3. Store private key in OS keychain (or encrypted file)
4. Store public key alongside for easy export
5. Display key ID and fingerprint

**Best Practices:**
- Use your real name and email for traceability
- Generate separate keys for different contexts (personal, work, team)
- Record key fingerprints in secure location
- Export and backup public key immediately

**Example Output:**
```
Signing key generated successfully!

Key Details:
  Key ID: a1b2c3d4e5f6g7h8
  Fingerprint: a1b2c3d4e5f6g7h8i9j0k1l2m3n4o5p6q7r8s9t0u1v2w3x4y5z6a7b8c9d0e1f2
  Name: John Doe
  Email: john@example.com
  Created: 2025-11-16 10:30:00

Keep your private key secure!
You can now sign bundles with: skillmeat bundle create --sign
```

---

## 4. Bundle Signing

### 4.1 Signing Process

**Command:**
```bash
skillmeat bundle create my-bundle --sign
```

**With specific key:**
```bash
skillmeat bundle create my-bundle --sign --signing-key-id a1b2c3d4e5f6g7h8
```

**Process:**
1. Build bundle (collect artifacts, compute hashes)
2. Generate bundle hash (SHA256 over manifest + artifact hashes)
3. Create canonical representation (deterministic JSON)
4. Sign with Ed25519 private key
5. Add signature to bundle manifest
6. Write signed bundle to file

**Signature Metadata:**
- Signature (base64-encoded, 64 bytes)
- Signer name and email
- Key fingerprint
- Timestamp (ISO 8601 UTC)
- Algorithm ("Ed25519")

**Example Signed Manifest:**
```json
{
  "bundle": {
    "name": "my-bundle",
    "version": "1.0.0",
    ...
  },
  "artifacts": [...],
  "bundle_hash": "abc123...",
  "signature": {
    "signature": "MEUCIQDw8...",
    "signer_name": "John Doe",
    "signer_email": "john@example.com",
    "key_fingerprint": "a1b2c3d4e5f6g7h8...",
    "signed_at": "2025-11-16T10:30:00Z",
    "algorithm": "Ed25519"
  }
}
```

---

### 4.2 When to Sign Bundles

**Required Signing:**
- Bundles distributed publicly
- Bundles shared across teams
- Production bundles
- Bundles uploaded to team vaults

**Optional Signing:**
- Personal bundles (not shared)
- Development/testing bundles
- Internal team bundles (trusted network)

**Recommendation:** Sign all bundles by default for best security.

---

## 5. Signature Verification

### 5.1 Verification Process

**Command:**
```bash
skillmeat sign verify my-bundle.skillmeat-pack
```

**Process:**
1. Extract bundle manifest
2. Check if bundle has signature
3. Load signer's public key by fingerprint
4. Verify key is in trust store
5. Recreate canonical representation
6. Verify Ed25519 signature
7. Report verification status

**Verification Statuses:**
- **VALID:** Signature is valid and key is trusted ✅
- **INVALID:** Signature is cryptographically invalid ❌
- **UNSIGNED:** Bundle has no signature ⚠️
- **KEY_NOT_FOUND:** Signing key not in trust store ⚠️
- **KEY_UNTRUSTED:** Key found but not trusted ⚠️
- **TAMPERED:** Bundle modified after signing ❌

---

### 5.2 Automatic Verification on Import

**Command:**
```bash
skillmeat bundle import bundle.skillmeat-pack
```

**Behavior:**
- Signature verified automatically if present
- Import fails if signature invalid
- Import warns if bundle unsigned
- Use `--force` to override verification failures (not recommended)

**Require Signature:**
```bash
skillmeat bundle import bundle.skillmeat-pack --require-signature
```

**Policy Recommendations:**
- Production imports: Always require signature
- Team imports: Require signature
- Personal imports: Verify if present
- Development: Optional verification

---

## 6. Key Distribution & Trust

### 6.1 Public Key Export

**Command:**
```bash
skillmeat sign export-key a1b2c3d4e5f6g7h8 -o john-doe.pub
```

**Output:** PEM-encoded Ed25519 public key
```
-----BEGIN PUBLIC KEY-----
MCowBQYDK2VwAyEAa1b2c3d4e5f6g7h8i9j0k1l2m3n4o5p6q7r8s9t0u1v2w3x=
-----END PUBLIC KEY-----
```

**Distribution Methods:**
- **Secure channels:** GPG-encrypted email, secure file sharing
- **Published:** Team wiki, internal documentation
- **Verified:** In-person verification at team meetings
- **Avoid:** Public GitHub, unencrypted email

---

### 6.2 Key Import & Trust

**Command:**
```bash
skillmeat sign import-key john-doe.pub \
  --name "John Doe" \
  --email "john@example.com" \
  --trust
```

**Trust Establishment:**

1. **Obtain Public Key:** Receive `.pub` file via secure channel
2. **Verify Fingerprint:** Confirm fingerprint out-of-band (phone, in-person, video call)
3. **Import with Trust:** Use `--trust` flag to mark as trusted
4. **Record Trust Decision:** Document why you trust this key

**Fingerprint Verification:**
```bash
# Sender provides fingerprint
Fingerprint: a1b2c3d4e5f6g7h8i9j0k1l2m3n4o5p6q7r8s9t0u1v2w3x4y5z6a7b8c9d0e1f2

# Recipient verifies after import
skillmeat sign list-keys --type trusted -v

# Compare fingerprints (must match exactly)
```

**Trust Levels:**
- **Trusted:** Accept signatures from this key
- **Untrusted:** Reject signatures (key imported for reference only)

**Web of Trust (Not Implemented):**
- SkillMeat uses a simple trust model (explicit trust only)
- No transitive trust (trusting A doesn't trust keys signed by A)
- Future: Consider implementing web of trust for team scenarios

---

## 7. Key Rotation

### 7.1 When to Rotate Keys

**Scheduled Rotation:**
- Every 12-24 months for long-term keys
- More frequently for high-security environments

**Emergency Rotation:**
- Private key compromised or suspected compromise
- Signing host compromised
- Employee departure (organizational keys)
- Algorithm deprecation or vulnerability

---

### 7.2 Rotation Procedure

**Step 1: Generate New Key**
```bash
skillmeat sign generate-key \
  --name "John Doe" \
  --email "john@example.com"
```

**Step 2: Export New Public Key**
```bash
skillmeat sign export-key <new-key-id> -o john-doe-new.pub
```

**Step 3: Distribute New Public Key**
- Send to all teams/users who trust your old key
- Include note about key rotation
- Provide both old and new fingerprints

**Step 4: Sign New Bundles with New Key**
```bash
skillmeat bundle create my-bundle --sign --signing-key-id <new-key-id>
```

**Step 5: Announce Rotation**
- Email teams: "I'm rotating my signing key. Old fingerprint: xxx, New fingerprint: yyy"
- Document rotation in team wiki
- Allow transition period (both keys valid)

**Step 6: Revoke Old Key (After Transition)**
```bash
skillmeat sign revoke <old-key-id> --type signing
```

**Transition Period:**
- **Recommended:** 30-90 days
- Sign with new key, but keep old key for verification
- After transition, revoke old key

---

### 7.3 Rotation Communication Template

```
Subject: Signing Key Rotation - John Doe

Team,

I'm rotating my SkillMeat bundle signing key as part of our regular
security practices.

Old Key:
  Fingerprint: a1b2c3d4e5f6g7h8i9j0k1l2m3n4o5p6q7r8s9t0u1v2w3x4y5z6a7b8c9d0e1f2
  Revocation Date: 2026-02-16

New Key:
  Fingerprint: b2c3d4e5f6g7h8i9j0k1l2m3n4o5p6q7r8s9t0u1v2w3x4y5z6a7b8c9d0e1f2g3
  Effective Date: 2025-11-16
  Public Key: Attached (john-doe-new.pub)

Actions Required:
1. Import my new public key:
   skillmeat sign import-key john-doe-new.pub --name "John Doe" --email "john@example.com" --trust

2. Verify fingerprint (call me at ext. 1234 or Slack DM):
   Fingerprint: b2c3d4e5f6g7h8i9...

3. After 2026-02-16, revoke my old key:
   skillmeat sign revoke a1b2c3d4e5f6g7h8 --type trusted

Let me know if you have any questions.

Thanks,
John
```

---

## 8. Key Revocation

### 8.1 Revoke Your Signing Key

**Command:**
```bash
skillmeat sign revoke a1b2c3d4e5f6g7h8 --type signing
```

**Impact:**
- Deletes private key permanently
- Cannot sign bundles with this key anymore
- Existing signatures remain valid (revocation doesn't invalidate old bundles)

**When to Revoke:**
- Key compromised
- Key no longer needed
- Rotating to new key (after transition)
- Leaving organization

**Warning:** This operation is irreversible!

---

### 8.2 Revoke Trusted Public Key

**Command:**
```bash
skillmeat sign revoke a1b2c3d4e5f6g7h8 --type trusted
```

**Impact:**
- Removes trust in this key
- Bundles signed with this key will fail verification
- Key can be re-imported if trust is re-established

**When to Revoke Trust:**
- Key owner reports compromise
- Key owner leaves organization
- Trust relationship ends
- Suspicious activity detected

---

### 8.3 Revocation Lists (Not Implemented)

**Future Enhancement:**
- Centralized revocation lists for organizations
- Automatic revocation checking
- Certificate Revocation List (CRL) style system
- Online Certificate Status Protocol (OCSP) for bundles

**Current Limitation:**
- Revocation is local only (per-user trust store)
- No central authority for revocations
- Users must manually revoke compromised keys

---

## 9. Security Best Practices

### 9.1 Key Management

**DO:**
- ✅ Generate separate keys for different contexts
- ✅ Store keys in OS keychain (preferred)
- ✅ Export and backup public keys
- ✅ Verify fingerprints out-of-band before trusting
- ✅ Rotate keys every 12-24 months
- ✅ Revoke keys immediately if compromised
- ✅ Use strong passphrases for encrypted file storage (if not using keychain)
- ✅ Sign all production and team-shared bundles

**DON'T:**
- ❌ Share private keys with anyone
- ❌ Store private keys in version control
- ❌ Email private keys (even encrypted)
- ❌ Trust keys without verifying fingerprints
- ❌ Use same key across multiple organizations
- ❌ Ignore key rotation schedules
- ❌ Import untrusted keys as trusted

---

### 9.2 Operational Security

**Bundle Creation:**
- Sign bundles before uploading to team vaults
- Verify signature immediately after signing
- Keep signing host secure (up-to-date, antivirus, firewall)
- Don't sign bundles on untrusted or shared computers
- Review artifacts before signing (avoid including secrets)

**Bundle Import:**
- Always verify signatures on downloaded bundles
- Require signatures for production imports
- Check signer identity matches expected source
- Review bundle contents before deploying
- Report unsigned bundles from expected-signed sources

**Trust Management:**
- Maintain list of trusted keys and their owners
- Review trusted keys quarterly
- Revoke keys when trust relationship ends
- Document trust decisions (why you trust a key)
- Verify fingerprints using multiple channels

---

### 9.3 Incident Response

**If Your Private Key is Compromised:**

1. **Immediately:**
   - Revoke the compromised key: `skillmeat sign revoke <key-id> --type signing`
   - Generate new key: `skillmeat sign generate-key`
   - Notify all teams who trust your key

2. **Within 24 Hours:**
   - Distribute new public key
   - Sign critical bundles with new key
   - Document incident for security review

3. **Within 1 Week:**
   - Review all bundles signed with compromised key
   - Re-sign critical bundles with new key
   - Update documentation and trust relationships

**If You Suspect a Trusted Key is Compromised:**

1. **Immediately:**
   - Revoke trust: `skillmeat sign revoke <key-id> --type trusted`
   - Notify key owner
   - Stop importing bundles from that source

2. **Investigate:**
   - Contact key owner to confirm compromise
   - Review recently imported bundles from that source
   - Check for tampering or malicious content

3. **Remediate:**
   - Re-import key if false alarm
   - Wait for new key if real compromise
   - Document incident

---

## 10. Organizational Policies

### 10.1 Individual Users

**Policy:**
- Signing is optional for personal bundles
- Verification recommended for imported bundles
- Key rotation every 24 months

---

### 10.2 Teams

**Policy:**
- All team-shared bundles MUST be signed
- Team members MUST import and trust team members' keys
- Key rotation every 12 months
- Fingerprint verification required (in-person or video call)
- Revoke keys within 24 hours of employee departure

**Team Key Registry:**
- Maintain spreadsheet or wiki page with:
  - Team member names
  - Key fingerprints
  - Key creation dates
  - Next rotation dates

**Example:**
| Name | Email | Fingerprint | Created | Rotate By |
|------|-------|-------------|---------|-----------|
| John Doe | john@example.com | a1b2c3... | 2025-01-15 | 2026-01-15 |
| Jane Smith | jane@example.com | b2c3d4... | 2025-03-20 | 2026-03-20 |

---

### 10.3 Organizations

**Policy:**
- All production bundles MUST be signed
- Bundle imports MUST verify signatures (--require-signature)
- Organizational signing key for official releases
- Individual keys for developer bundles
- Key rotation every 12 months
- Centralized key registry with audit trail
- Mandatory key revocation procedures

**Organizational Signing Key:**
- Stored in HSM (Hardware Security Module) or secure vault
- Multi-party control (2-of-3 key holders)
- Used only for official releases
- Strict access controls and logging

**Compliance:**
- SOC 2: Key management procedures documented
- ISO 27001: Regular key rotation and access review
- GDPR: Audit trail for key operations

---

## 11. Cryptographic Details

### 11.1 Signing Process

**Input:**
- Bundle manifest (JSON)
- Bundle hash (SHA256)
- Private signing key (Ed25519)

**Canonical Representation:**
```json
{
  "bundle_hash": "sha256_hash_of_manifest_and_artifacts",
  "manifest": {
    "bundle": {...},
    "artifacts": [...],
    // signature field removed
    // created_at field removed (non-canonical)
  }
}
```

**Signature Computation:**
1. Serialize canonical JSON with sorted keys, no whitespace
2. Compute SHA256 of canonical JSON → message_hash
3. Sign message_hash with Ed25519 private key → signature (64 bytes)
4. Base64-encode signature → signature_b64

**Signature Metadata:**
```json
{
  "signature": "base64_encoded_64_byte_signature",
  "signer_name": "John Doe",
  "signer_email": "john@example.com",
  "key_fingerprint": "sha256_of_public_key",
  "signed_at": "2025-11-16T10:30:00Z",
  "algorithm": "Ed25519"
}
```

---

### 11.2 Verification Process

**Input:**
- Bundle with embedded signature
- Signer's public key (from trust store)

**Verification Steps:**
1. Extract signature metadata from manifest
2. Lookup signer's public key by fingerprint
3. Verify key is trusted
4. Recreate canonical representation (remove signature field)
5. Serialize to canonical JSON
6. Compute SHA256 → message_hash
7. Verify Ed25519 signature using public key
8. Check signature timestamp (optional, prevent replay)

**Verification Result:**
- **Pass:** Signature valid, key trusted, bundle unchanged
- **Fail:** Signature invalid, key not trusted, bundle tampered

---

### 11.3 Security Properties

**Ed25519 Guarantees:**
- **Unforgeability:** Cannot create valid signature without private key
- **Non-repudiation:** Only private key holder could have signed
- **Integrity:** Any change to bundle invalidates signature
- **Authenticity:** Public key proves signer identity

**Attack Resistance:**
- **Signature forgery:** Computationally infeasible (2^128 security level)
- **Key recovery:** Cannot derive private key from public key
- **Collision attacks:** SHA256 fingerprints are collision-resistant
- **Replay attacks:** Timestamp in signature (checked by verifier)

---

## 12. Troubleshooting

### 12.1 Common Issues

**Problem: "No signing key available"**
```
Solution:
skillmeat sign generate-key --name "Your Name" --email "you@example.com"
```

**Problem: "Signer key not found in trust store"**
```
Solution:
1. Obtain signer's public key (.pub file)
2. Verify fingerprint with signer
3. Import: skillmeat sign import-key signer.pub --name "Signer" --email "signer@example.com" --trust
```

**Problem: "Invalid signature - bundle may be tampered"**
```
Possible Causes:
- Bundle was modified after signing
- Wrong public key imported (fingerprint mismatch)
- Corrupted bundle file during transfer

Solution:
1. Re-download bundle from trusted source
2. Verify fingerprint matches expected signer
3. Contact bundle creator if issue persists
```

**Problem: "Keychain not available"**
```
Solution:
- macOS: Ensure Keychain Access app is running
- Windows: Check Credential Manager service is running
- Linux: Install gnome-keyring or kwallet
- Fallback: SkillMeat will use encrypted file storage automatically
```

---

## 13. Compliance & Audit

### 13.1 Audit Trail

**Events Logged:**
- Key generation (key ID, timestamp, user)
- Key import (key ID, fingerprint, trusted status)
- Key revocation (key ID, type, timestamp)
- Bundle signing (bundle name, key ID, timestamp)
- Signature verification (bundle, status, timestamp)

**Log Location:**
- Event tracking database: `~/.skillmeat/analytics/events.db`
- Python logs: Configurable via logging configuration

**Retention:**
- Recommended: 12 months minimum
- Compliance: Match organizational data retention policy

---

### 13.2 Audit Checklist

**Quarterly Review:**
- [ ] Review all trusted public keys
- [ ] Verify key owners still require trust
- [ ] Check for keys approaching rotation deadline
- [ ] Revoke keys for departed employees
- [ ] Verify signing key backups exist
- [ ] Review bundle signing practices

**Annual Review:**
- [ ] Rotate all organizational keys
- [ ] Review and update signing policy
- [ ] Audit key management procedures
- [ ] Train team on security best practices
- [ ] Document compliance with security standards

---

## 14. References

### 14.1 Standards

- **RFC 8032:** Edwards-Curve Digital Signature Algorithm (EdDSA)
- **FIPS 186-5:** Digital Signature Standard (DSS)
- **NIST SP 800-57:** Recommendation for Key Management

### 14.2 Libraries

- **cryptography:** Python cryptographic library (https://cryptography.io/)
- **keyring:** Python keyring library (https://github.com/jaraco/keyring)

### 14.3 Further Reading

- [Ed25519: high-speed high-security signatures](https://ed25519.cr.yp.to/)
- [The Cryptographic Doom Principle](https://moxie.org/2011/12/13/the-cryptographic-doom-principle.html)
- [OWASP Key Management Cheat Sheet](https://cheatsheetseries.owasp.org/cheatsheets/Key_Management_Cheat_Sheet.html)

---

## Document Control

**Version History:**

| Version | Date | Author | Changes |
|---------|------|--------|---------|
| 1.0 | 2025-11-16 | Security Team | Initial signing policy |

**Next Review:** 2026-11-16 (12 months)

**Approvals:**

- [ ] Security Lead
- [ ] Engineering Lead
- [ ] Compliance Officer
