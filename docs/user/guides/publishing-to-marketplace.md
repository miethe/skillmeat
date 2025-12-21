# Publishing to SkillMeat Marketplace

This guide walks you through publishing your artifact bundles to the SkillMeat marketplace.

## Table of Contents

- [Prerequisites](#prerequisites)
- [Understanding the Publishing Process](#understanding-the-publishing-process)
- [Preparing Your Bundle](#preparing-your-bundle)
- [Publishing Workflow](#publishing-workflow)
- [Validation Requirements](#validation-requirements)
- [Best Practices](#best-practices)
- [Troubleshooting](#troubleshooting)

## Prerequisites

Before publishing to the marketplace, ensure you have:

1. **A Valid Bundle**: A `.skillmeat-pack` bundle file containing your artifacts
2. **Metadata**: Complete publishing metadata including:
   - Title (5-100 characters)
   - Description (100-5000 characters)
   - Tags (1-10 valid tags)
   - SPDX license identifier
   - Publisher information (name and email)
3. **SkillMeat CLI**: Version 1.0.0 or higher installed

## Understanding the Publishing Process

The publishing workflow consists of several stages:

```
1. Bundle Preparation
   └─> Load and validate bundle file

2. Metadata Validation
   └─> Validate title, description, tags, license, publisher

3. License Compatibility Check
   └─> Verify SPDX license and artifact compatibility

4. Security Scanning
   ├─> Scan for secrets (API keys, tokens, passwords)
   ├─> Check for malicious patterns (eval, exec, shell commands)
   ├─> Validate file types
   └─> Enforce size limits

5. Submission
   └─> Submit to marketplace broker for review

6. Review Process
   ├─> Pending: Submitted, awaiting review
   ├─> In Review: Under active review
   ├─> Approved: Published to marketplace
   ├─> Rejected: Declined with feedback
   └─> Revision Requested: Needs changes
```

## Preparing Your Bundle

### 1. Create Your Bundle

First, create a bundle from your collection:

```bash
# Build bundle from specific artifacts
skillmeat bundle-build my-bundle \
  --artifact skill:my-skill \
  --artifact command:my-command \
  --output my-bundle.skillmeat-pack

# Build bundle from entire collection
skillmeat bundle-build comprehensive \
  --all-artifacts \
  --output comprehensive-bundle.skillmeat-pack
```

### 2. Prepare Publishing Metadata

Create a metadata file (optional) or prepare CLI arguments:

**metadata.json:**
```json
{
  "title": "Productivity Power Tools",
  "description": "A comprehensive collection of productivity-enhancing Claude skills and commands. Includes document processing, data analysis, automation workflows, and more. Perfect for developers and knowledge workers looking to supercharge their Claude experience.",
  "tags": ["productivity", "automation", "development"],
  "license": "MIT",
  "publisher": {
    "name": "Jane Developer",
    "email": "jane@example.com",
    "homepage": "https://janedeveloper.com"
  },
  "homepage": "https://github.com/jane/productivity-tools",
  "repository": "https://github.com/jane/productivity-tools",
  "documentation": "https://productivity-tools.readthedocs.io",
  "price": 0
}
```

### 3. Choose Appropriate Tags

Valid marketplace tags:

- `productivity` - Tools that enhance productivity
- `documentation` - Documentation generation and management
- `development` - Software development tools
- `testing` - Testing and QA tools
- `data-analysis` - Data processing and analytics
- `automation` - Workflow automation
- `ai-ml` - AI and machine learning tools
- `web-dev` - Web development tools
- `backend` - Backend development
- `frontend` - Frontend development
- `database` - Database tools
- `security` - Security tools
- `devops` - DevOps and infrastructure
- `cloud` - Cloud platform tools
- `api` - API development and testing
- `cli` - Command-line tools
- `education` - Educational resources
- `research` - Research tools
- `creative` - Creative and design tools
- `business` - Business tools

### 4. Validate Your License

Ensure you use a valid SPDX license identifier. Common licenses:

- `MIT` - Permissive, allows commercial use
- `Apache-2.0` - Permissive with patent grant
- `GPL-3.0-only` - Copyleft, requires source disclosure
- `LGPL-3.0-only` - Weak copyleft, allows linking
- `BSD-3-Clause` - Permissive with attribution
- `CC0-1.0` - Public domain dedication

See [SPDX License List](https://spdx.org/licenses/) for all valid identifiers.

## Publishing Workflow

### Basic Publishing

```bash
skillmeat marketplace-publish my-bundle.skillmeat-pack \
  --title "Productivity Power Tools" \
  --description "A comprehensive collection of productivity-enhancing Claude skills..." \
  --tags "productivity,automation,development" \
  --license "MIT" \
  --publisher-name "Jane Developer" \
  --publisher-email "jane@example.com" \
  --repository "https://github.com/jane/productivity-tools"
```

### Dry Run (Validation Only)

Test your bundle without actually publishing:

```bash
skillmeat marketplace-publish my-bundle.skillmeat-pack \
  --title "My Bundle" \
  --description "..." \
  --tags "productivity" \
  --license "MIT" \
  --publisher-name "John Doe" \
  --publisher-email "john@example.com" \
  --dry-run
```

### Advanced Options

```bash
skillmeat marketplace-publish my-bundle.skillmeat-pack \
  --title "My Bundle" \
  --description "..." \
  --tags "productivity,automation" \
  --license "MIT" \
  --publisher-name "Jane Developer" \
  --publisher-email "jane@example.com" \
  --homepage "https://example.com" \
  --repository "https://github.com/jane/repo" \
  --documentation "https://docs.example.com" \
  --price 999 \
  --broker "skillmeat" \
  --force
```

**Options:**
- `--broker` - Choose marketplace broker (default: skillmeat)
- `--price` - Price in cents (0 = free, >0 = paid)
- `--dry-run` - Validate without publishing
- `--skip-security` - Skip security scanning (not recommended!)
- `--force` - Bypass warnings

## Validation Requirements

Your bundle must pass all validation checks before publishing:

### 1. Bundle Integrity

- Valid ZIP file format
- Manifest present and valid
- Bundle hash matches content
- Signature valid (if signed)

### 2. Metadata Requirements

- **Title**: 5-100 characters
- **Description**: 100-5000 characters (detailed, not just a tagline)
- **Tags**: 1-10 valid tags from allowed list
- **License**: Valid SPDX identifier
- **Publisher Name**: Non-empty, max 100 characters
- **Publisher Email**: Valid email format
- **URLs**: Valid HTTP/HTTPS URLs (if provided)

### 3. License Compatibility

Your bundle license must be compatible with all artifact licenses:

**Compatible Combinations:**
- MIT bundle with MIT/Apache/BSD artifacts ✓
- GPL bundle with GPL/LGPL/MIT artifacts ✓
- Apache bundle with Apache/MIT/BSD artifacts ✓

**Incompatible Combinations:**
- GPL bundle with proprietary artifacts ✗
- MIT bundle with GPL artifacts (warning)

### 4. Security Requirements

**Blocked Content:**
- API keys and tokens (AWS, GitHub, Slack, etc.)
- Private keys and certificates
- Passwords and credentials
- Database connection strings
- Binary executables (.exe, .dll, .so)

**Suspicious Patterns (warnings):**
- `eval()` and `exec()` in Python
- `shell=True` in subprocess
- Shell command injection patterns
- Obfuscated code

**Size Limits:**
- Maximum bundle size: 100 MB
- Maximum artifact count: 1,000 artifacts

### 5. File Type Validation

**Allowed Extensions:**
- Source code: `.py`, `.js`, `.ts`, `.jsx`, `.tsx`
- Documentation: `.md`, `.txt`, `.html`
- Configuration: `.json`, `.toml`, `.yaml`, `.yml`, `.ini`
- Scripts: `.sh`, `.bash`, `.zsh`, `.fish`
- Data: `.csv`, `.sql`, `.xml`, `.graphql`

**Blocked Extensions:**
- Executables: `.exe`, `.dll`, `.so`, `.dylib`, `.bin`
- Installers: `.deb`, `.rpm`, `.msi`, `.dmg`, `.pkg`
- Mobile apps: `.apk`, `.ipa`

**Warning Extensions (sensitive):**
- `.env`, `.key`, `.pem`, `.cert`, `.crt`

## Best Practices

### 1. Write Clear Descriptions

**Good Description:**
```
A comprehensive suite of productivity tools for Claude, designed to streamline
document processing, automate repetitive tasks, and enhance data analysis
workflows. Includes 15 skills covering PDF generation, Excel manipulation,
email automation, and more. Perfect for knowledge workers, researchers, and
developers who want to maximize their efficiency with Claude.

Features:
- PDF generation with custom templates
- Excel data processing and visualization
- Email automation and templating
- Document format conversion
- Web scraping and data extraction
```

**Poor Description:**
```
Some useful tools
```

### 2. Choose Relevant Tags

- Use 3-5 tags that accurately describe your bundle
- Choose the most specific tags available
- Don't use all 10 tags just to maximize visibility

### 3. Provide Complete URLs

- **Homepage**: Your project website or landing page
- **Repository**: GitHub/GitLab repository with source code
- **Documentation**: Full documentation site or README

### 4. License Considerations

- Choose a license that matches your intent
- Verify all artifact licenses are compatible
- Document any third-party code dependencies
- Consider using `MIT` or `Apache-2.0` for maximum compatibility

### 5. Security Best Practices

**Before Publishing:**
1. Review all files for secrets
2. Remove `.env` files and credentials
3. Scan with `git-secrets` or similar tools
4. Remove unnecessary binary files
5. Validate file types

**Code Quality:**
- Avoid using `eval()` and `exec()`
- Use parameterized queries for databases
- Sanitize user inputs
- Minimize shell command usage

### 6. Pre-Publication Checklist

- [ ] Bundle builds successfully
- [ ] All artifacts tested individually
- [ ] Documentation is complete and clear
- [ ] License file included
- [ ] No secrets or credentials in bundle
- [ ] File types are appropriate
- [ ] Description is detailed (100+ chars)
- [ ] Tags accurately describe content
- [ ] URLs are valid and accessible
- [ ] Dry-run validation passes

## Troubleshooting

### Common Validation Errors

#### "Description too short"

**Problem**: Description must be at least 100 characters.

**Solution**: Expand your description to provide more detail about what your bundle includes and who it's for.

```bash
# Bad (20 chars)
--description "Useful tools"

# Good (150+ chars)
--description "A collection of 10 productivity-focused Claude skills for document processing, including PDF generation, Excel manipulation, and email automation. Ideal for knowledge workers."
```

#### "Invalid tags"

**Problem**: One or more tags are not in the allowed list.

**Solution**: Use only valid tags from the marketplace list.

```bash
# Bad
--tags "my-tag,custom-category"

# Good
--tags "productivity,automation,development"
```

#### "License validation failed"

**Problem**: Invalid SPDX license identifier or incompatible licenses.

**Solution**: Use a valid SPDX identifier and ensure compatibility.

```bash
# Bad
--license "My Custom License"

# Good
--license "MIT"
```

#### "Security violation: Potential AWS key found"

**Problem**: Security scanner detected a potential secret.

**Solution**: Remove all secrets from your bundle.

```python
# Bad - Hardcoded secret
AWS_KEY = "AKIAIOSFODNN7EXAMPLE"

# Good - Use environment variable
import os
AWS_KEY = os.environ.get("AWS_KEY")
```

#### "Blocked file type: .exe"

**Problem**: Bundle contains a binary executable.

**Solution**: Remove binary files or use source code instead.

### Getting Help

If you encounter issues:

1. **Review Validation Output**: Read error messages carefully
2. **Check Documentation**: Refer to this guide and SPDX documentation
3. **Use Dry Run**: Test with `--dry-run` before publishing
4. **Contact Support**: Email marketplace@skillmeat.com for assistance

### Monitoring Submission Status

After publishing, track your submission:

```bash
# View submission status
skillmeat marketplace-status <submission-id>

# List all your submissions
skillmeat marketplace-submissions --publisher "your@email.com"
```

**Submission States:**
- `pending` - Submitted, awaiting review
- `in_review` - Under active review
- `approved` - Published to marketplace
- `rejected` - Declined with feedback
- `revision_requested` - Needs changes

### Handling Rejection

If your submission is rejected:

1. **Review Feedback**: Check rejection message for specific issues
2. **Address Issues**: Fix identified problems
3. **Resubmit**: Create new submission after corrections

```bash
# View rejection details
skillmeat marketplace-status <submission-id>

# Fix issues and resubmit
skillmeat marketplace-publish updated-bundle.skillmeat-pack \
  --title "..." \
  --description "..." \
  # ... other metadata
```

## Pricing Your Bundle

### Free Bundles

Most bundles are free (price = 0):

```bash
--price 0
```

### Paid Bundles

For paid bundles, set price in cents:

```bash
# $9.99
--price 999

# $49.00
--price 4900
```

**Considerations:**
- Free bundles get more downloads
- Paid bundles require marketplace payment setup
- Consider "freemium" model (free basic, paid premium)

## Updates and Versioning

To update a published bundle:

1. Increment bundle version
2. Create new bundle with changes
3. Publish as update to existing listing
4. Include changelog in description

```bash
# Update bundle version in metadata
skillmeat bundle-build my-bundle \
  --version 2.0.0 \
  --artifact skill:my-skill \
  --output my-bundle-v2.skillmeat-pack

# Publish update
skillmeat marketplace-publish my-bundle-v2.skillmeat-pack \
  --title "My Bundle v2.0" \
  --description "Version 2.0 - Now includes...\n\nChangelog:\n- Added feature X\n- Fixed bug Y" \
  # ... other metadata
```

## Legal Considerations

### Copyright

- You must own or have rights to all content
- Respect third-party copyrights
- Include proper attribution

### Licensing

- Choose appropriate license for your use case
- Understand license implications
- Ensure compatibility with dependencies

### Trademarks

- Don't use trademarked names without permission
- Don't impersonate other publishers
- Be clear about third-party integrations

## Conclusion

Publishing to the SkillMeat marketplace is straightforward when you:

1. Prepare complete, accurate metadata
2. Choose appropriate licenses
3. Ensure security best practices
4. Test thoroughly before submission

For additional help, visit:
- [SkillMeat Documentation](https://docs.skillmeat.com)
- [SPDX License List](https://spdx.org/licenses/)
- [Support Forum](https://forum.skillmeat.com)

Happy publishing!
