# Attribution Requirements Guide

This guide explains attribution requirements for different open source licenses and how to properly credit third-party software in your SkillMeat bundles.

## Table of Contents

- [What is Attribution?](#what-is-attribution)
- [Why Attribution Matters](#why-attribution-matters)
- [Licenses Requiring Attribution](#licenses-requiring-attribution)
- [Attribution Formats](#attribution-formats)
- [Automated Attribution Tools](#automated-attribution-tools)
- [Common Scenarios](#common-scenarios)

## What is Attribution?

Attribution is the act of crediting the original authors of software you use or distribute. It typically includes:

- **Copyright notices** - Who created the work and when
- **License information** - Under what terms the work is licensed
- **Source references** - Where to find the original work
- **Modification notes** - Changes you made to the original

## Why Attribution Matters

1. **Legal Compliance** - Many licenses require attribution
2. **Ethical Practice** - Respect for creators and their work
3. **Transparency** - Users know what software they're using
4. **Community Health** - Encourages open source contribution
5. **Marketplace Requirements** - SkillMeat requires proper attribution

## Licenses Requiring Attribution

### Strong Attribution Requirements

These licenses have explicit attribution requirements:

#### MIT License
**Requirements:**
- Preserve copyright notice
- Preserve license text
- Include in all copies or substantial portions

**Example:**
```markdown
Copyright (c) 2024 Original Author
Permission is hereby granted, free of charge...
```

#### Apache-2.0 License
**Requirements:**
- Preserve copyright notice
- Preserve NOTICE file (if present)
- State modifications made
- Include copy of license

**Example:**
```markdown
Copyright 2024 Original Author

Licensed under the Apache License, Version 2.0
NOTICE: Modified files X, Y, Z
```

#### BSD Licenses (2-Clause, 3-Clause)
**Requirements:**
- Preserve copyright notice
- Preserve license text
- Preserve disclaimer

**Example:**
```markdown
Copyright (c) 2024, Original Author
All rights reserved.

Redistribution and use in source and binary forms...
```

#### ISC License
**Requirements:**
- Preserve copyright notice
- Preserve permission notice

**Example:**
```markdown
Copyright (c) 2024 Original Author

Permission to use, copy, modify, and/or distribute...
```

### Copyleft Licenses

GPL and AGPL also require attribution plus additional requirements:

#### GPL-3.0 / AGPL-3.0
**Requirements:**
- Preserve all copyright notices
- Preserve all license notices
- Provide copy of GPL
- State modifications prominently
- Provide source code access

### No Attribution Required

Some licenses don't require attribution but it's still good practice:

- **CC0-1.0** (Public Domain)
- **Unlicense**
- **WTFPL**

## Attribution Formats

### CREDITS.md File

The standard way to provide attribution in SkillMeat bundles:

```markdown
# Credits and Attributions

This bundle includes the following third-party software:

## requests
- **License**: Apache-2.0
- **Copyright**: Copyright (c) Kenneth Reitz
- **Source**: https://github.com/psf/requests
- **Modifications**: None

## click
- **License**: BSD-3-Clause
- **Copyright**: Copyright (c) 2014 Armin Ronacher
- **Source**: https://github.com/pallets/click
- **Modifications**: None

## my-utility (modified)
- **License**: MIT
- **Copyright**: Copyright (c) 2024 Utility Author
- **Source**: https://github.com/author/my-utility
- **Modifications**: Added feature X, fixed bug Y
```

### NOTICE File (Apache-2.0)

Apache-2.0 projects may include a NOTICE file:

```
SkillMeat Bundle Name

This product includes software developed by contributors
listed in the CREDITS file.

Apache-Licensed Components:

- requests: Copyright (c) Kenneth Reitz
  https://github.com/psf/requests

- httpx: Copyright (c) Tom Christie
  https://github.com/encode/httpx
```

### Source File Headers

Add attribution in source file headers:

```python
# SPDX-License-Identifier: MIT
# Copyright (c) 2024 Your Name
#
# Portions based on original-project (MIT License)
# Copyright (c) 2023 Original Author
# https://github.com/author/original-project

def my_function():
    # Implementation
    pass
```

### README.md Section

Include attribution in README:

```markdown
# My Bundle

## Credits

This bundle uses the following open source projects:

- [requests](https://github.com/psf/requests) - Apache-2.0
- [click](https://github.com/pallets/click) - BSD-3-Clause
- [pytest](https://github.com/pytest-dev/pytest) - MIT

See CREDITS.md for full attribution details.
```

## Automated Attribution Tools

SkillMeat provides tools to help with attribution:

### Scan for Dependencies

```bash
# Scan bundle for license information
skillmeat compliance-scan bundle.zip

# Output shows:
# - All detected licenses
# - Copyright notices found
# - Files missing attribution
# - Recommendations
```

### Generate CREDITS File

```bash
# Extract attributions from bundle
# Creates CREDITS.md automatically

# Example output:
# Credits extracted: 5 components
# CREDITS.md created
```

### Validate Attributions

```bash
# Check if attributions are complete
skillmeat compliance-checklist bundle.zip

# Validates:
# - CREDITS file exists
# - All dependencies credited
# - Copyright notices present
# - NOTICE file (if Apache-2.0)
```

## Common Scenarios

### Scenario 1: Using MIT Dependencies

**Dependencies:**
- `requests` (Apache-2.0)
- `click` (BSD-3-Clause)
- `pytest` (MIT)

**Your Bundle License:** MIT

**Attribution Required:**
1. Create CREDITS.md listing all three
2. Preserve their copyright notices
3. Include their license texts (or reference)

**CREDITS.md:**
```markdown
# Credits and Attributions

## requests
- **License**: Apache-2.0
- **Copyright**: Copyright (c) Kenneth Reitz
- **Source**: https://github.com/psf/requests
- **Modifications**: None

## click
- **License**: BSD-3-Clause
- **Copyright**: Copyright (c) 2014 Armin Ronacher
- **Source**: https://github.com/pallets/click
- **Modifications**: None

## pytest
- **License**: MIT
- **Copyright**: Copyright (c) 2004 Holger Krekel and others
- **Source**: https://github.com/pytest-dev/pytest
- **Modifications**: None
```

### Scenario 2: Apache-2.0 Bundle

**Your Bundle License:** Apache-2.0

**Dependencies:** Multiple Apache-2.0 libraries

**Attribution Required:**
1. Create CREDITS.md
2. Create NOTICE file
3. List all Apache dependencies in NOTICE
4. Document any modifications

**NOTICE:**
```
My Bundle Name

Apache-Licensed Components:

- httpx: Copyright (c) Tom Christie
  https://github.com/encode/httpx

- pydantic: Copyright (c) Samuel Colvin
  https://github.com/pydantic/pydantic
```

### Scenario 3: Modified Dependency

**Original:** `utility-lib` (MIT)
**Your Changes:** Added feature X, fixed bug Y

**Attribution:**
```markdown
## utility-lib (modified)
- **License**: MIT
- **Copyright**: Copyright (c) 2024 Original Author
- **Source**: https://github.com/author/utility-lib
- **Modifications**:
  - Added feature X for better performance
  - Fixed bug Y in edge case handling
```

### Scenario 4: Embedded Code Snippet

**Used:** 10 lines from Stack Overflow (CC BY-SA 4.0)

**Attribution:**
```python
# The following function is based on code from Stack Overflow
# Question: https://stackoverflow.com/q/12345678
# Author: Username (CC BY-SA 4.0)
# Modifications: Adapted for use with async/await

def my_function():
    # Code here
    pass
```

### Scenario 5: Public Domain Code

**Used:** Algorithm from public domain source

**Attribution (optional but recommended):**
```python
# Algorithm based on public domain implementation
# Reference: https://example.com/algorithm
# No copyright claimed on original implementation

def algorithm():
    pass
```

## Best Practices

### 1. Track Dependencies Early

As soon as you add a dependency:
```bash
# Add to CREDITS.md immediately
echo "## new-dependency" >> CREDITS.md
echo "- License: MIT" >> CREDITS.md
echo "- Copyright: (c) 2024 Author" >> CREDITS.md
```

### 2. Use Dependency Management

Track licenses in your dependency files:

**pyproject.toml:**
```toml
[tool.skillmeat.dependencies]
requests = { version = "2.31.0", license = "Apache-2.0" }
click = { version = "8.1.0", license = "BSD-3-Clause" }
```

### 3. Automate License Collection

Use tools to extract licenses:
```bash
# Python
pip-licenses --format=markdown > licenses.md

# Node.js
license-checker --markdown > licenses.md

# Then integrate into CREDITS.md
```

### 4. Include Full License Texts

For small numbers of dependencies, include full texts:

```
licenses/
├── MIT.txt
├── Apache-2.0.txt
└── BSD-3-Clause.txt
```

Reference in CREDITS.md:
```markdown
- **License**: MIT (see licenses/MIT.txt)
```

### 5. Document Modifications Clearly

Be specific about changes:
```markdown
**Modifications**:
- 2024-01-15: Added async support
- 2024-02-20: Fixed memory leak in parser
- 2024-03-10: Updated to Python 3.11
```

## Checklist

Before publishing your bundle:

- [ ] CREDITS.md file created
- [ ] All dependencies listed in CREDITS.md
- [ ] Copyright notices preserved
- [ ] License texts included or referenced
- [ ] NOTICE file created (if using Apache-2.0)
- [ ] Modifications documented
- [ ] Source URLs provided
- [ ] Attribution validated with SkillMeat tools

## Common Mistakes

### ❌ Missing CREDITS File
```
# No CREDITS.md in bundle
# SkillMeat will reject during validation
```

### ✅ Include CREDITS File
```markdown
# CREDITS.md in bundle root
# Lists all third-party software
```

### ❌ Incomplete Attribution
```markdown
## requests
- License: Apache-2.0
# Missing copyright and source!
```

### ✅ Complete Attribution
```markdown
## requests
- **License**: Apache-2.0
- **Copyright**: Copyright (c) Kenneth Reitz
- **Source**: https://github.com/psf/requests
- **Modifications**: None
```

### ❌ No Modification Notes
```markdown
## my-lib (modified)
- License: MIT
# What modifications?!
```

### ✅ Clear Modification Notes
```markdown
## my-lib (modified)
- **License**: MIT
- **Copyright**: (c) 2024 Author
- **Modifications**: Added feature X, removed deprecated API
```

## Resources

- [SkillMeat Compliance Guide](./compliance-guide.md)
- [SPDX License List](https://spdx.org/licenses/)
- [Producing OSS: Legal Matters](https://producingoss.com/en/legal.html)
- [Google Open Source Docs: Attribution](https://opensource.google/documentation/reference/thirdparty/attribution)

## Need Help?

```bash
# Scan your bundle
skillmeat compliance-scan bundle.zip

# Generate checklist
skillmeat compliance-checklist bundle.zip

# Get attribution requirements
skillmeat compliance-checklist bundle.zip --license Apache-2.0
```

For complex attribution scenarios, consult the SkillMeat community or seek legal advice.
