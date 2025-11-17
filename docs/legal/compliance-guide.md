# Legal Compliance Guide for Publishers

This guide helps publishers understand and meet the legal compliance requirements for publishing bundles on the SkillMeat marketplace.

## Table of Contents

- [Overview](#overview)
- [License Selection](#license-selection)
- [Compliance Requirements by License Type](#compliance-requirements-by-license-type)
- [Common Pitfalls](#common-pitfalls)
- [Conflict Resolution](#conflict-resolution)
- [Best Practices](#best-practices)

## Overview

When publishing a bundle to the SkillMeat marketplace, you must ensure that:

1. All code has appropriate licenses
2. License compatibility is maintained
3. Attribution requirements are met
4. Legal obligations are documented and consented to

The compliance system helps automate these checks and provides clear guidance on requirements.

## License Selection

### Choosing the Right License

Consider these factors when selecting a license:

**Permissive Licenses** (MIT, Apache-2.0, BSD)
- **Pros**: Easy to use, minimal restrictions, wide adoption
- **Cons**: No patent protection (except Apache-2.0), derivatives can be proprietary
- **Best for**: Libraries, tools, components meant for broad use

**Copyleft Licenses** (GPL-3.0, AGPL-3.0)
- **Pros**: Ensures derivatives remain open source, strong community protection
- **Cons**: More restrictive, can limit commercial use, incompatible with some licenses
- **Best for**: Applications, projects prioritizing open source ecosystem

**Weak Copyleft** (LGPL, MPL)
- **Pros**: Balance between permissive and copyleft, allows proprietary integration
- **Cons**: More complex compliance requirements
- **Best for**: Libraries that should remain open but allow proprietary use

### SPDX Identifiers

Always use valid SPDX license identifiers:

```python
# Good - Clear SPDX identifier
# SPDX-License-Identifier: MIT

# Bad - Custom or unclear license
# License: My Custom License
```

## Compliance Requirements by License Type

### MIT License

**Required:**
- LICENSE file with full MIT text
- Copyright notices in all source files
- Preserve license and copyright in distributions

**Checklist Items:**
- [ ] All files have license headers
- [ ] LICENSE file present
- [ ] Copyright notices accurate
- [ ] No proprietary code without permission
- [ ] No secrets in code

**Example Header:**
```python
# SPDX-License-Identifier: MIT
# Copyright (c) 2024 Your Name

def my_function():
    pass
```

### Apache-2.0 License

**Required:**
- LICENSE file with Apache 2.0 text
- Copyright notices in all source files
- NOTICE file if dependencies require it
- Patent grant understanding

**Checklist Items:**
- [ ] All files have license headers
- [ ] LICENSE file present
- [ ] Copyright notices accurate
- [ ] NOTICE file created (if needed)
- [ ] Patent grant implications understood

**Example Header:**
```python
# SPDX-License-Identifier: Apache-2.0
# Copyright 2024 Your Name
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.

def my_function():
    pass
```

### GPL-3.0 License

**Required:**
- LICENSE file with GPL-3.0 text
- Source code included or accessible
- Modifications clearly marked
- Same license for derivatives
- Preserve original copyright notices

**Checklist Items:**
- [ ] All files have GPL headers
- [ ] LICENSE file present
- [ ] Source code included
- [ ] Modifications documented
- [ ] Same license applied to derivatives
- [ ] Original copyrights preserved

**Example Header:**
```python
# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (C) 2024 Your Name
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.

def my_function():
    pass
```

### Proprietary/Commercial License

**Required:**
- Explicit permission to redistribute
- Clear license agreement terms
- Commercial use explicitly allowed
- Written permission from copyright holders

**Checklist Items:**
- [ ] Permission to redistribute obtained
- [ ] License agreement documented
- [ ] Commercial use allowed
- [ ] Terms clear and accessible

## Common Pitfalls

### 1. Missing License Headers

**Problem:** Files without SPDX identifiers or license headers

**Solution:**
```bash
# Add to all source files
# SPDX-License-Identifier: MIT
# Copyright (c) 2024 Your Name
```

### 2. License Conflicts

**Problem:** Mixing incompatible licenses (e.g., GPL-2.0 + Apache-2.0)

**Solution:**
- Use GPL-3.0 instead of GPL-2.0 (compatible with Apache)
- Remove conflicting dependencies
- Obtain alternative licenses

### 3. Missing Attributions

**Problem:** No CREDITS file for dependencies

**Solution:**
```bash
# Generate CREDITS file
skillmeat compliance-scan bundle.zip

# Create CREDITS.md manually:
# Credits and Attributions
## Dependency Name
- License: MIT
- Copyright: (c) 2024 Author
- Source: https://github.com/author/dep
```

### 4. Copyright Notice Errors

**Problem:** Outdated or missing copyright years

**Solution:**
```python
# Keep copyright current
# Copyright (c) 2023-2024 Your Name

# Or use single year
# Copyright (c) 2024 Your Name
```

### 5. Secrets in Code

**Problem:** API keys, passwords, or tokens in source

**Solution:**
```bash
# Use environment variables
API_KEY = os.environ.get("API_KEY")

# Use config files (gitignored)
with open(".env") as f:
    config = load_config(f)

# Never commit secrets
echo ".env" >> .gitignore
```

## Conflict Resolution

### GPL-2.0 + Apache-2.0 Conflict

**Issue:** GPL-2.0 is incompatible with Apache-2.0 due to patent clause

**Resolution:**
1. **Upgrade to GPL-3.0** (compatible with Apache-2.0)
2. **Remove Apache-2.0 components** and find GPL-compatible alternatives
3. **Contact Apache-2.0 authors** for dual licensing

### Multiple Copyleft Licenses

**Issue:** GPL-3.0 + AGPL-3.0 in same bundle

**Resolution:**
1. **Choose single license** (AGPL is stricter, so use AGPL)
2. **Separate into multiple bundles** with distinct licenses
3. **Obtain permission** for re-licensing components

### Permissive + Copyleft

**Issue:** MIT + GPL-3.0 creates copyleft requirement

**Resolution:**
1. **Accept copyleft** - bundle must be GPL-3.0
2. **Separate bundles** - keep MIT components separate
3. **Document clearly** which parts are which license

## Best Practices

### 1. License Early

Choose and document your license from the start:

```bash
# Create LICENSE file immediately
cp /path/to/MIT-LICENSE ./LICENSE

# Add headers to all new files
# Use editor templates or pre-commit hooks
```

### 2. Maintain CREDITS File

Keep attribution up-to-date:

```markdown
# CREDITS.md

## requests
- License: Apache-2.0
- Copyright: (c) Kenneth Reitz
- Source: https://github.com/psf/requests

## click
- License: BSD-3-Clause
- Copyright: (c) Armin Ronacher
- Source: https://github.com/pallets/click
```

### 3. Use Automated Tools

Let SkillMeat help:

```bash
# Scan for compliance issues
skillmeat compliance-scan bundle.zip

# Generate checklist
skillmeat compliance-checklist bundle.zip

# Record consent
skillmeat compliance-consent <checklist-id> --publisher-email you@example.com
```

### 4. Document Dependencies

Track all third-party code:

```toml
# dependencies.toml
[[dependencies]]
name = "requests"
version = "2.31.0"
license = "Apache-2.0"
source = "https://github.com/psf/requests"

[[dependencies]]
name = "click"
version = "8.1.0"
license = "BSD-3-Clause"
source = "https://github.com/pallets/click"
```

### 5. Review Before Publishing

Pre-publication checklist:

- [ ] All files have license headers
- [ ] LICENSE file is correct and complete
- [ ] CREDITS.md lists all dependencies
- [ ] NOTICE file created (if Apache-2.0)
- [ ] No secrets or credentials in code
- [ ] Copyright years are current
- [ ] No license conflicts detected
- [ ] Attribution requirements understood
- [ ] Compliance checklist completed

## Getting Help

### Compliance Scanning

```bash
# Scan bundle for licenses
skillmeat compliance-scan my-bundle.zip

# Output shows:
# - Declared license
# - Detected licenses per file
# - Conflicts
# - Missing licenses
# - Recommendations
```

### Checklist Generation

```bash
# Generate license-specific checklist
skillmeat compliance-checklist my-bundle.zip --license MIT

# Review all requirements
# Complete each item
# Record consent
```

### Conflict Resolution

```bash
# If scanner detects conflicts:
# 1. Review conflict details
# 2. Choose resolution strategy
# 3. Update code/licenses
# 4. Re-scan to verify
```

## Legal Disclaimer

This guide provides general information about software licensing and is not legal advice. For specific legal questions about your bundle, consult a qualified attorney.

The SkillMeat compliance tools help identify potential issues but do not guarantee legal compliance. Publishers are solely responsible for ensuring their bundles comply with all applicable laws and licenses.

## Resources

- [SPDX License List](https://spdx.org/licenses/)
- [Choose a License](https://choosealicense.com/)
- [GNU License Compatibility](https://www.gnu.org/licenses/license-list.html)
- [Apache License FAQ](https://www.apache.org/foundation/license-faq.html)
- [OSI Approved Licenses](https://opensource.org/licenses)
