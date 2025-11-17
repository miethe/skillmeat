# SkillMeat Threat Model

**Version**: 1.0
**Date**: 2025-11-17
**Scope**: SkillMeat v0.3.0-beta (All Phases 0-4)
**Classification**: Internal

---

## Executive Summary

This document presents a comprehensive threat model for SkillMeat, a personal collection manager for Claude Code configurations. The threat model identifies critical assets, potential threat actors, attack vectors, and mitigations across all system components.

**Risk Level**: MEDIUM
**Primary Concerns**: Bundle integrity, credential security, marketplace trust

---

## 1. Assets

### 1.1 Critical Assets

| Asset | Description | Confidentiality | Integrity | Availability |
|-------|-------------|-----------------|-----------|--------------|
| User Collections | Local artifact collections in `~/.skillmeat/collections/` | HIGH | HIGH | MEDIUM |
| Bundle Signatures | Ed25519 cryptographic signatures for bundles | N/A | CRITICAL | HIGH |
| Signing Keys | Private Ed25519 keys for bundle signing | CRITICAL | CRITICAL | HIGH |
| Auth Tokens | JWT tokens for CLI-to-web authentication | HIGH | HIGH | MEDIUM |
| Publisher Keys | Ed25519 keys for marketplace publishing | CRITICAL | CRITICAL | HIGH |
| MCP Settings | Claude Desktop configuration and env files | HIGH | HIGH | HIGH |
| GitHub Tokens | Personal access tokens for GitHub operations | CRITICAL | HIGH | MEDIUM |
| User Data | Usage analytics and preferences | MEDIUM | LOW | LOW |
| Vault Credentials | Git SSH keys, S3 credentials for team vaults | CRITICAL | HIGH | HIGH |

### 1.2 Asset Value Analysis

**Highest Value Assets:**
1. **Signing Keys**: Compromise allows forging trusted bundles
2. **GitHub Tokens**: Access to user repositories and private code
3. **Vault Credentials**: Access to shared team artifacts
4. **Auth Tokens**: Full access to local SkillMeat operations

---

## 2. Threat Actors

### 2.1 External Threat Actors

**Malicious Publisher**
- **Motivation**: Financial gain, reputation damage, data theft
- **Capabilities**: Can publish bundles to marketplace
- **Access Level**: Marketplace publisher account
- **Threat Level**: HIGH

**Network Attacker (Man-in-the-Middle)**
- **Motivation**: Intercept credentials, inject malicious bundles
- **Capabilities**: Network interception, TLS downgrade attacks
- **Access Level**: Network layer access
- **Threat Level**: MEDIUM

**Malicious Bundle Author**
- **Motivation**: Code execution, data exfiltration
- **Capabilities**: Create bundles with hidden malicious code
- **Access Level**: Public bundle creation
- **Threat Level**: HIGH

**Supply Chain Attacker**
- **Motivation**: Compromise SkillMeat dependencies
- **Capabilities**: Publish malicious packages to PyPI
- **Access Level**: PyPI ecosystem
- **Threat Level**: MEDIUM

### 2.2 Internal Threat Actors

**Local Attacker (Same Machine)**
- **Motivation**: Access to local collections, steal keys
- **Capabilities**: File system access, process inspection
- **Access Level**: User or root access on same machine
- **Threat Level**: MEDIUM

**Compromised Process**
- **Motivation**: Exploit SkillMeat vulnerabilities
- **Capabilities**: Memory access, file operations
- **Access Level**: User process permissions
- **Threat Level**: MEDIUM

---

## 3. Attack Vectors

### 3.1 Bundle Security

**AV-001: Bundle Tampering During Transit**
- **Description**: Attacker intercepts bundle download and modifies contents
- **Impact**: Installation of malicious artifacts
- **Likelihood**: MEDIUM
- **Severity**: HIGH
- **Mitigations**:
  - Ed25519 signature verification on all bundles
  - SHA-256 hash verification before import
  - HTTPS-only downloads from marketplace
  - Certificate validation enforced

**AV-002: Signature Bypass or Forgery**
- **Description**: Attacker attempts to forge bundle signatures
- **Impact**: Installation of unsigned/malicious bundles
- **Likelihood**: LOW
- **Severity**: CRITICAL
- **Mitigations**:
  - Ed25519 signatures (mathematically secure)
  - Key fingerprint verification
  - Trusted key registry
  - No signature = installation warning

**AV-003: Malicious Bundle with Secrets**
- **Description**: Bundle contains hardcoded credentials, API keys
- **Impact**: Credential leakage when shared
- **Likelihood**: MEDIUM
- **Severity**: HIGH
- **Mitigations**:
  - Security scanner detects 40+ secret patterns
  - Pre-publish scanning for AWS keys, GitHub tokens, etc.
  - `.env` file detection and warnings
  - Private key detection (PEM, SSH keys)

**AV-004: Malicious Code in Artifacts**
- **Description**: Artifacts contain eval(), exec(), shell injection
- **Impact**: Code execution on user's machine
- **Likelihood**: HIGH
- **Severity**: HIGH
- **Mitigations**:
  - Pattern matching for dangerous functions (eval, exec)
  - Shell command detection (rm -rf /, curl | sh)
  - Installation warnings about code execution
  - No automatic execution during installation

**AV-005: Path Traversal in Bundle Extraction**
- **Description**: Bundle contains `../../../etc/passwd` entries
- **Impact**: Write files outside collection directory
- **Likelihood**: LOW
- **Severity**: HIGH
- **Mitigations**:
  - Path validation using `Path.resolve()`
  - Relative path checking
  - Extraction to temporary directory
  - Atomic move to final location

**AV-006: Zip Bomb Attack**
- **Description**: Bundle with 1MB compressed -> 10GB uncompressed
- **Impact**: Disk space exhaustion, DoS
- **Likelihood**: LOW
- **Severity**: MEDIUM
- **Mitigations**:
  - Bundle size limits (100MB max)
  - Artifact count limits (1000 max)
  - Compression ratio checks (future enhancement)

---

### 3.2 Authentication & Authorization

**AV-007: Authentication Token Theft**
- **Description**: Attacker steals JWT token from file system
- **Impact**: Full access to SkillMeat operations
- **Likelihood**: MEDIUM
- **Severity**: HIGH
- **Mitigations**:
  - Tokens stored in OS keychain (macOS, Windows, Linux)
  - Fallback to encrypted file storage
  - File permissions 0600 (user-only access)
  - Token expiration (90 days default)
  - Token revocation support

**AV-008: Rate Limit Bypass**
- **Description**: Attacker sends excessive API requests
- **Impact**: DoS, resource exhaustion
- **Likelihood**: MEDIUM
- **Severity**: MEDIUM
- **Mitigations**:
  - Rate limiting: 100 req/hr general, 10 req/hr sensitive
  - Per-IP tracking (future enhancement)
  - Token-based rate limits
  - Exponential backoff on failures

**AV-009: Session Hijacking**
- **Description**: Attacker steals active session token
- **Impact**: Unauthorized operations
- **Likelihood**: LOW
- **Severity**: HIGH
- **Mitigations**:
  - JWT tokens (stateless, no session storage)
  - Token expiration enforced
  - No token refresh (expired = re-authenticate)
  - HTTPS-only API communication

---

### 3.3 Secrets Management

**AV-010: Secrets Leakage in Bundles**
- **Description**: Publisher accidentally includes `.env` file in bundle
- **Impact**: Credential exposure to all bundle users
- **Likelihood**: HIGH
- **Severity**: HIGH
- **Mitigations**:
  - Security scanner detects `.env` files
  - Pre-publish warnings for sensitive files
  - `.gitignore`-style exclusions
  - Manual review before publish

**AV-011: Private Keys in Bundle**
- **Description**: Bundle contains `.pem`, `.key` files
- **Impact**: Cryptographic key compromise
- **Likelihood**: MEDIUM
- **Severity**: CRITICAL
- **Mitigations**:
  - Security scanner blocks private key patterns
  - File extension validation (`.pem`, `.key` flagged)
  - Content scanning for `-----BEGIN PRIVATE KEY-----`

**AV-012: MCP Environment File Exposure**
- **Description**: MCP server env files contain credentials
- **Impact**: Service credentials leaked
- **Likelihood**: HIGH
- **Severity**: HIGH
- **Mitigations**:
  - Deployment warnings for env files
  - Backup created before deployment
  - User confirmation required
  - Documentation on secure env file management

---

### 3.4 Network Security

**AV-013: Man-in-the-Middle (MitM) Attacks**
- **Description**: Attacker intercepts marketplace downloads
- **Impact**: Malicious bundle installation
- **Likelihood**: LOW
- **Severity**: HIGH
- **Mitigations**:
  - HTTPS required for all downloads
  - Certificate validation enabled
  - No HTTP fallback
  - Signature verification after download

**AV-014: DNS Spoofing**
- **Description**: Attacker redirects marketplace domain
- **Impact**: Download from malicious server
- **Likelihood**: LOW
- **Severity**: MEDIUM
- **Mitigations**:
  - HTTPS with certificate validation
  - Signature verification (prevents trust even if downloaded)
  - Marketplace domain pinning (future enhancement)

---

### 3.5 File System Security

**AV-015: Local File Access**
- **Description**: Attacker with local access reads collections
- **Impact**: Access to user artifacts and configurations
- **Likelihood**: MEDIUM
- **Severity**: MEDIUM
- **Mitigations**:
  - Collection directory permissions 0755
  - Config directory permissions 0700
  - Config file permissions 0600
  - OS keychain for sensitive data

**AV-016: Signing Key Theft**
- **Description**: Attacker accesses signing keys on disk
- **Impact**: Ability to sign malicious bundles
- **Likelihood**: LOW
- **Severity**: CRITICAL
- **Mitigations**:
  - Primary: OS keychain storage
  - Fallback: Encrypted file storage
  - File permissions 0600
  - Passphrase protection (optional)

---

### 3.6 Supply Chain Security

**AV-017: Dependency Vulnerabilities**
- **Description**: Vulnerable dependencies in SkillMeat
- **Impact**: Exploitable vulnerabilities in production
- **Likelihood**: MEDIUM
- **Severity**: MEDIUM-HIGH
- **Mitigations**:
  - Automated dependency scanning (Dependabot)
  - Regular `safety` and `pip-audit` checks
  - Version pinning with minimum versions
  - Security advisories monitored

**AV-018: Malicious Dependency**
- **Description**: Compromised PyPI package
- **Impact**: Code execution during installation
- **Likelihood**: LOW
- **Severity**: CRITICAL
- **Mitigations**:
  - Minimal dependency count
  - Well-known, trusted libraries only
  - Package hash verification (future enhancement)
  - Regular security audits

---

## 4. Attack Trees

### 4.1 Compromise User Collection

```
[ROOT] Compromise User Collection
├── [OR] Install Malicious Bundle
│   ├── [AND] Bypass Signature Verification
│   │   ├── Forge Ed25519 signature (LOW likelihood)
│   │   └── Exploit signature validation bug (LOW)
│   ├── [AND] Tamper with Bundle During Download
│   │   ├── MitM attack (MEDIUM)
│   │   └── DNS spoofing (LOW)
│   └── [AND] Publisher Publishes Malicious Bundle
│       ├── Compromise publisher account (MEDIUM)
│       └── Bypass security scanning (MEDIUM)
├── [OR] Direct File System Access
│   ├── Local attacker with user access (MEDIUM)
│   └── Root access on machine (HIGH impact, LOW likelihood)
└── [OR] Exploit SkillMeat Vulnerability
    ├── Path traversal during extraction (LOW)
    └── Code injection in CLI commands (LOW)
```

### 4.2 Steal Signing Keys

```
[ROOT] Steal Signing Keys
├── [OR] File System Access
│   ├── Read encrypted key file (MEDIUM likelihood)
│   │   └── [AND] Decrypt file
│   │       ├── Derive encryption key (deterministic) (MEDIUM)
│   │       └── Access encrypted file (MEDIUM)
│   └── Access OS keychain (LOW)
│       └── Requires OS-level authentication
├── [OR] Memory Dump
│   ├── Dump SkillMeat process memory (LOW)
│   └── Extract key material from RAM (LOW)
└── [OR] Social Engineering
    └── Trick user into exporting key (MEDIUM)
```

---

## 5. Mitigations Summary

### 5.1 Implemented Mitigations

**Cryptographic Security**
- Ed25519 digital signatures for all bundles
- SHA-256 hash verification
- OS keychain integration for key storage
- Encrypted file storage fallback (Fernet + PBKDF2)

**Bundle Validation**
- Path traversal prevention
- File type validation (blocklist: `.exe`, `.dll`, `.so`)
- Size limits (100MB bundles, 1000 artifacts)
- Secret detection (40+ patterns)
- Malicious pattern detection (eval, exec, shell commands)

**Authentication**
- JWT bearer tokens
- Token expiration (90 days)
- Token revocation support
- OS keychain storage

**Network Security**
- HTTPS-only downloads
- Certificate validation
- No HTTP fallback

**File Permissions**
- Config directory: 0700
- Config files: 0600
- Collection directory: 0755
- Key files: 0600 (when using file storage)

**Input Validation**
- Pydantic models for all API inputs
- SPDX license validation
- Tag whitelist enforcement
- URL format validation

### 5.2 Recommended Enhancements

**High Priority**
1. Implement compression ratio checks (zip bomb prevention)
2. Add passphrase protection for file-based key storage
3. Implement certificate pinning for marketplace
4. Add audit logging for security events

**Medium Priority**
1. Generate Software Bill of Materials (SBOM)
2. Add IP-based rate limiting
3. Implement token refresh mechanism
4. Add hardware security key support for signing

**Low Priority**
1. Add 2FA for publisher accounts
2. Implement key rotation automation
3. Add security scanning results to bundle metadata
4. Create security dashboard in web UI

---

## 6. Risk Matrix

| Risk ID | Threat | Likelihood | Impact | Risk Level | Mitigation Status |
|---------|--------|------------|--------|------------|------------------|
| AV-001 | Bundle tampering | MEDIUM | HIGH | HIGH | ✅ MITIGATED |
| AV-002 | Signature forgery | LOW | CRITICAL | MEDIUM | ✅ MITIGATED |
| AV-003 | Secrets in bundles | MEDIUM | HIGH | HIGH | ✅ MITIGATED |
| AV-004 | Malicious code | HIGH | HIGH | HIGH | ⚠️ PARTIALLY MITIGATED |
| AV-005 | Path traversal | LOW | HIGH | MEDIUM | ✅ MITIGATED |
| AV-006 | Zip bomb | LOW | MEDIUM | LOW | ⚠️ NEEDS IMPROVEMENT |
| AV-007 | Token theft | MEDIUM | HIGH | HIGH | ✅ MITIGATED |
| AV-008 | Rate limit bypass | MEDIUM | MEDIUM | MEDIUM | ⚠️ PARTIALLY MITIGATED |
| AV-009 | Session hijacking | LOW | HIGH | MEDIUM | ✅ MITIGATED |
| AV-010 | Secrets leakage | HIGH | HIGH | HIGH | ✅ MITIGATED |
| AV-011 | Private keys in bundle | MEDIUM | CRITICAL | HIGH | ✅ MITIGATED |
| AV-012 | MCP env exposure | HIGH | HIGH | HIGH | ⚠️ PARTIALLY MITIGATED |
| AV-013 | MitM attacks | LOW | HIGH | MEDIUM | ✅ MITIGATED |
| AV-014 | DNS spoofing | LOW | MEDIUM | LOW | ✅ MITIGATED |
| AV-015 | Local file access | MEDIUM | MEDIUM | MEDIUM | ✅ MITIGATED |
| AV-016 | Signing key theft | LOW | CRITICAL | MEDIUM | ✅ MITIGATED |
| AV-017 | Dependency vulns | MEDIUM | MEDIUM-HIGH | MEDIUM | ⚠️ ONGOING |
| AV-018 | Malicious dependency | LOW | CRITICAL | MEDIUM | ⚠️ PARTIALLY MITIGATED |

**Risk Distribution:**
- **HIGH**: 3 (16.7%)
- **MEDIUM**: 12 (66.7%)
- **LOW**: 3 (16.7%)

---

## 7. Compliance Mapping

### 7.1 OWASP Top 10 (2021)

| OWASP Risk | Relevance | SkillMeat Mitigation |
|------------|-----------|---------------------|
| A01: Broken Access Control | HIGH | JWT auth, token validation, file permissions |
| A02: Cryptographic Failures | HIGH | Ed25519, OS keychain, encrypted storage |
| A03: Injection | MEDIUM | Input validation, no SQL/command injection |
| A04: Insecure Design | MEDIUM | Threat modeling, security-first architecture |
| A05: Security Misconfiguration | MEDIUM | Secure defaults, file permissions |
| A06: Vulnerable Components | HIGH | Dependency scanning, version pinning |
| A07: Authentication Failures | HIGH | JWT tokens, expiration, OS keychain |
| A08: Software & Data Integrity | HIGH | Signature verification, hash checks |
| A09: Security Logging | MEDIUM | Event logging, analytics tracking |
| A10: SSRF | LOW | No user-controlled URLs |

### 7.2 CWE Top 25 (2023)

**Addressed CWEs:**
- CWE-22 (Path Traversal): ✅ Mitigated
- CWE-78 (Command Injection): ✅ Mitigated
- CWE-79 (XSS): ✅ N/A (no HTML rendering)
- CWE-89 (SQL Injection): ✅ N/A (no SQL database)
- CWE-200 (Information Exposure): ✅ Mitigated
- CWE-287 (Authentication): ✅ Mitigated
- CWE-319 (Cleartext Transmission): ✅ Mitigated (HTTPS)
- CWE-502 (Deserialization): ⚠️ Partial (ZIP extraction validated)
- CWE-732 (Incorrect Permissions): ✅ Mitigated

---

## 8. Incident Response

### 8.1 Security Incident Scenarios

**Scenario 1: Compromised Signing Key**
1. Revoke compromised key immediately
2. Generate new signing key
3. Re-sign all published bundles
4. Notify users of key rotation
5. Investigate key compromise source

**Scenario 2: Malicious Bundle Published**
1. Remove bundle from marketplace
2. Revoke bundle signature
3. Notify users who downloaded bundle
4. Investigate publisher account
5. Add bundle hash to blocklist

**Scenario 3: Dependency Vulnerability**
1. Assess vulnerability severity
2. Update dependency to patched version
3. Release security update
4. Notify users to update
5. Add to security advisory

---

## 9. Review and Maintenance

**Review Frequency**: Quarterly

**Next Review**: 2026-02-17

**Threat Model Owners:**
- Security Lead
- Engineering Lead

**Review Triggers:**
- New feature additions
- Significant architecture changes
- Security incidents
- Regulatory requirement changes

---

## 10. References

- OWASP Threat Modeling: https://owasp.org/www-community/Threat_Modeling
- STRIDE Methodology: https://learn.microsoft.com/en-us/azure/security/develop/threat-modeling-tool-threats
- CWE Top 25: https://cwe.mitre.org/top25/
- NIST Cybersecurity Framework: https://www.nist.gov/cyberframework

---

**Document Control:**

| Version | Date | Author | Changes |
|---------|------|--------|---------|
| 1.0 | 2025-11-17 | Security Review Task P5-004 | Initial threat model |

**Approvals:**

- [ ] Security Lead
- [ ] Engineering Lead
- [ ] Product Owner

---

**Classification**: Internal
**Last Updated**: 2025-11-17
