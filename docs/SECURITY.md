# Security Policy

## Supported Versions

SkillMeat is currently in alpha release. Security updates will be provided for:

| Version | Supported          |
| ------- | ------------------ |
| 0.1.0-alpha   | :white_check_mark: |

## Reporting a Vulnerability

If you discover a security vulnerability in SkillMeat, please report it by:

1. **DO NOT** open a public GitHub issue
2. Email the maintainers at: [Create a private security advisory on GitHub](https://github.com/miethe/skillmeat/security/advisories/new)
3. Include:
   - Description of the vulnerability
   - Steps to reproduce
   - Potential impact
   - Suggested fix (if available)

We will respond within 72 hours and work with you to address the issue promptly.

## Security Considerations

### Artifact Execution

**IMPORTANT**: SkillMeat manages Claude Code artifacts that execute code and access system resources. Always review artifacts before adding them to your collection.

- Skills can execute arbitrary code through Claude
- Commands run shell commands and scripts
- Agents have autonomous capabilities
- MCP servers can access system resources
- Hooks execute during session lifecycle events

**Best Practices**:
- Only add artifacts from trusted sources
- Review artifact contents before deployment
- Use `skillmeat verify <spec>` to inspect artifacts before adding
- Pay attention to security warnings during `add` operations
- Use `--dangerously-skip-permissions` flag only when you fully trust the source

### GitHub Token Security

GitHub tokens stored in SkillMeat configuration have repository access:

**Protection Measures**:
- Tokens are stored in `~/.skillmeat/config.toml` with user-only permissions (0600)
- Tokens are NEVER logged or printed to console
- Tokens are only used for GitHub API authentication
- Use fine-grained personal access tokens with minimal scopes

**Recommended Token Scopes**:
- `public_repo` (for public repositories only)
- `repo` (only if you need private repository access)

**Token Management**:
```bash
# Set token
skillmeat config set github-token <token>

# Remove token
skillmeat config unset github-token

# Verify token is not exposed
grep -r "ghp_" ~/.skillmeat/  # Should only appear in config.toml
```

### Path Traversal Protection

SkillMeat validates all file paths to prevent path traversal attacks:

**Protections**:
- All paths are resolved to absolute paths using `Path.resolve()`
- Parent directory references (`..`) are validated
- Symbolic links are followed and validated
- Collection and artifact paths are restricted to expected directories

**Safe Operations**:
```python
# Internal validation ensures paths stay within boundaries
artifact_path = collection_dir / artifact_type.value / artifact_name
deployment_path = project_dir / ".claude" / artifact_type.value / artifact_name
```

### File Permissions

SkillMeat handles file permissions securely:

**Directory Permissions**:
- Collection directories: 0755 (rwxr-xr-x)
- Config directory: 0700 (rwx------)

**File Permissions**:
- Config files: 0600 (rw-------)
- Artifact files: 0644 (rw-r--r--)
- Executable artifacts: 0755 (rwxr-xr-x)

**Windows Considerations**:
- Read-only files are handled by removing read-only attribute before operations
- NTFS permissions are preserved during copy operations

### Snapshot Security

Snapshots contain complete artifact copies:

**Considerations**:
- Snapshots may include sensitive data from artifacts
- Snapshots are stored in `~/.skillmeat/collections/<name>/snapshots/`
- Old snapshots should be cleaned periodically
- Snapshot files have user-only read/write permissions

**Best Practices**:
```bash
# List all snapshots
skillmeat history

# Remove old snapshots manually if needed
rm -rf ~/.skillmeat/collections/personal/snapshots/<snapshot-id>

# Or clean up automatically (future feature)
skillmeat snapshot clean --older-than 30d
```

### Network Security

GitHub API interactions use HTTPS:

**Protections**:
- All GitHub API calls use HTTPS (TLS 1.2+)
- Certificate validation is enabled by default
- Rate limiting is respected
- Tokens are sent via Authorization header (not URL)

**Dependencies**:
- `requests` library handles TLS/SSL
- `GitPython` uses system git for HTTPS clones
- No custom certificate handling

### Configuration Security

Configuration files contain sensitive data:

**Protection**:
- Config directory created with 0700 permissions
- Config file (`config.toml`) has 0600 permissions
- No world-readable configuration files
- No environment variable expansion (prevents injection)

**Sensitive Configuration Keys**:
- `github-token`: GitHub personal access token

**Non-Sensitive Configuration Keys**:
- `default-collection`: Name of default collection
- `auto-update`: Auto-update check preference

## Known Security Limitations

### Alpha Release Limitations

1. **No Code Signing**: Artifacts are not cryptographically signed
2. **No Provenance Tracking**: No verification of artifact authenticity beyond GitHub
3. **No Sandboxing**: Artifacts execute with user permissions
4. **No Audit Log**: No persistent logging of artifact operations
5. **No Access Control**: Single-user tool with no multi-user permissions

### Planned Security Enhancements (Future)

- Artifact signature verification
- Provenance tracking via SLSA framework
- Integration with Claude's artifact verification
- Audit logging for compliance
- Team-based access controls (v2.0)

## Security Best Practices for Users

### Before Adding Artifacts

1. **Verify Source**: Use `skillmeat verify <spec>` to inspect
2. **Check GitHub Repo**: Review repository for red flags
3. **Read Documentation**: Understand what the artifact does
4. **Check Permissions**: See what access the artifact requires
5. **Review Code**: Inspect artifact contents before deployment

### During Operation

1. **Least Privilege**: Only grant GitHub token minimal necessary scopes
2. **Regular Updates**: Keep SkillMeat and artifacts updated
3. **Monitor Changes**: Review `skillmeat status` for unexpected updates
4. **Snapshot Before Updates**: Use `skillmeat snapshot` before major changes
5. **Clean Up**: Remove unused artifacts with `skillmeat remove`

### After Incidents

1. **Revoke Tokens**: If compromised, revoke GitHub token immediately
2. **Check Artifacts**: Review all artifacts for unexpected changes
3. **Rollback**: Use `skillmeat rollback` to restore known-good state
4. **Report**: If incident involves SkillMeat security, report privately

## Security Audit Results

Last security audit: 2025-11-08

**Findings**:
- ✅ No arbitrary code execution during add/deploy (only during artifact use)
- ✅ GitHub tokens never logged or exposed
- ✅ Path operations use Path.resolve() for safety
- ✅ File permissions properly set for sensitive files
- ✅ No SQL injection (no database used)
- ✅ No command injection (no shell=True in subprocess calls)
- ✅ Input validation on artifact names, types, and specs
- ✅ Atomic file operations prevent partial writes

**Recommendations**:
- Continue using Path operations instead of string concatenation
- Maintain token security practices
- Add artifact signature verification in future releases
- Consider adding audit logging for enterprise users

## Dependency Security

SkillMeat dependencies are monitored for vulnerabilities:

**Core Dependencies**:
- `click` - CLI framework
- `rich` - Terminal formatting
- `GitPython` - Git operations
- `requests` - HTTP client
- `PyYAML` - YAML parsing
- `tomli`/`tomli_w` - TOML parsing

**Security Updates**:
- Dependencies are updated regularly
- Security advisories monitored via GitHub Dependabot
- Minimum version requirements specified in `pyproject.toml`

**Checking for Vulnerabilities**:
```bash
# Using pip-audit
pip install pip-audit
pip-audit

# Using safety
pip install safety
safety check
```

## Compliance

SkillMeat is designed for individual developer use:

- **GDPR**: No personal data collection or transmission
- **License Compliance**: MIT license, permissive for commercial use
- **Data Residency**: All data stored locally, no cloud services
- **Privacy**: No telemetry, analytics, or tracking

## Questions?

For security-related questions that are not vulnerabilities:
- Open a GitHub Discussion
- Tag with `security` label
- Check existing security documentation

---

**Last Updated**: 2025-11-08
**Security Point of Contact**: See [SECURITY.md](https://github.com/miethe/skillmeat/security)
