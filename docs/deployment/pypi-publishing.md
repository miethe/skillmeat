---
title: PyPI Publishing Procedure
description: End-to-end guide for publishing skillmeat to PyPI
audience: maintainers
---

# PyPI Publishing Procedure

This document covers the complete procedure for publishing skillmeat to PyPI, from
prerequisites through verification. The automated path uses GitHub Actions with OIDC
Trusted Publishers; the manual path is documented for emergencies and local testing.

---

## Prerequisites

### Accounts and Access

| Requirement | Purpose |
|-------------|---------|
| PyPI account at pypi.org | Production publishing |
| TestPyPI account at test.pypi.org | Pre-release validation |
| GitHub repository write access | Tag creation and release |
| `RELEASE_PAT` secret in repo | Triggers cross-workflow dispatch |

### PyPI Trusted Publisher Configuration

skillmeat uses OIDC Trusted Publishers — no long-lived API tokens are stored in
GitHub secrets. The publisher must be registered once on PyPI before the workflow
can publish.

**Register on PyPI:**

1. Log in to https://pypi.org and navigate to your account settings
2. Go to **Publishing** → **Add a new pending publisher**
3. Fill in:
   - **PyPI Project Name**: `skillmeat`
   - **Owner**: `miethe`
   - **Repository name**: `skillmeat`
   - **Workflow name**: `publish-pypi.yml`
   - **Environment name**: `pypi`

Repeat the same steps on https://test.pypi.org with environment name `testpypi`.

**GitHub Environment Setup:**

Create two GitHub Environments in the repository settings:

- `pypi` — used for production publishing; set **Required reviewers** and **Deployment protection rules** as appropriate
- `testpypi` — used for test publishing

The `id-token: write` permission in `.github/workflows/publish-pypi.yml` is what
enables OIDC exchange. No additional secrets are needed.

---

## Automated Publish (CI Path)

The full release pipeline is:

```
git tag v<version> → push tag → release.yml creates GitHub Release
  → publish-pypi.yml triggered (workflow_dispatch) → builds + checks + publishes to PyPI
  → release-package.yml creates standalone artifacts and attaches to Release
```

### Step-by-step

1. **Bump the version** in `pyproject.toml` and commit:

   ```bash
   # Edit pyproject.toml: version = "<new-version>"
   git add pyproject.toml
   git commit -m "chore: bump version to <new-version>"
   ```

   See the **Version Bump Checklist** section below for all locations to update.

2. **Tag the commit:**

   ```bash
   git tag v<new-version>
   git push origin main --tags
   ```

3. **Monitor workflows** in the GitHub Actions tab:

   - `release.yml` creates the GitHub Release and dispatches `publish-pypi.yml`
   - `publish-pypi.yml` builds, runs `twine check`, and publishes to PyPI
   - `release-package.yml` builds standalone executables and uploads to the Release

4. **Verify** the package is live:

   ```bash
   pip install skillmeat==<new-version>
   skillmeat --version
   ```

### Pre-release Tags

Tags containing `alpha`, `beta`, or `rc` are automatically marked as pre-releases
by `release.yml`:

```bash
git tag v1.0.0-alpha.1
git push origin v1.0.0-alpha.1
```

---

## Manual Publish (Emergency / Local Testing)

Use this path when CI is unavailable or for publishing to TestPyPI before a production
release.

### Requirements

```bash
pip install build twine
```

### Build

```bash
# Clean previous dist artifacts
rm -rf dist/ build/ *.egg-info/

# Build both sdist and wheel
python -m build --sdist --wheel

# Verify distributions
python -m twine check dist/*
```

Expected output:

```
Checking dist/skillmeat-<version>-py3-none-any.whl: PASSED
Checking dist/skillmeat-<version>.tar.gz: PASSED
```

### Publish to TestPyPI (validate first)

```bash
python -m twine upload --repository testpypi dist/*
```

You will be prompted for your TestPyPI credentials unless you use an API token:

```bash
python -m twine upload --repository testpypi \
  --username __token__ --password <testpypi-api-token> dist/*
```

Verify the TestPyPI install:

```bash
pip install --index-url https://test.pypi.org/simple/ skillmeat==<version>
skillmeat --version
```

### Publish to PyPI (production)

```bash
python -m twine upload dist/*
# or with token:
python -m twine upload --username __token__ --password <pypi-api-token> dist/*
```

### Configure `.pypirc` (optional, avoids repeated credential entry)

```ini
[distutils]
index-servers =
    pypi
    testpypi

[pypi]
repository = https://upload.pypi.org/legacy/
username = __token__
password = pypi-<your-api-token>

[testpypi]
repository = https://test.pypi.org/legacy/
username = __token__
password = pypi-<your-testpypi-token>
```

Store this at `~/.pypirc` with `chmod 600 ~/.pypirc`.

---

## Version Bump Checklist

Before tagging a release, update version strings in all of these locations:

| File | Field | Example |
|------|-------|---------|
| `pyproject.toml` | `version = "..."` | `version = "1.0.0"` |
| `skillmeat/__init__.py` | `__version__` | `__version__ = "1.0.0"` |
| `CHANGELOG.md` | New section header | `## [1.0.0] - 2026-01-15` |

Verify the version is consistent before tagging:

```bash
python -c "import skillmeat; print(skillmeat.__version__)"
python -m build --sdist --wheel 2>&1 | grep "Successfully built"
```

See `.claude/specs/version-bump-spec.md` for the authoritative version bump procedure.

---

## Metadata Audit Notes

The current `pyproject.toml` is PyPI-publishing-ready. Verified state:

| Field | Status | Notes |
|-------|--------|-------|
| `name` | OK | `skillmeat` |
| `version` | OK | Follows SemVer |
| `description` | OK | One-line summary |
| `readme` | OK | Points to `README.md` (Markdown) |
| `license` | OK | `{file = "LICENSE"}` (MIT) |
| `classifiers` | OK | Development status, license, OS, Python versions, topics |
| `requires-python` | OK | `>=3.9` |
| `authors` | OK | SkillMeat Contributors |
| `keywords` | OK | 9 relevant keywords |
| `project.urls` | OK | Homepage, Documentation, Repository, Issues |

**Upcoming deprecation (2027-02-18):** setuptools will stop supporting the
`project.license = {file = "..."}` table syntax and the
`License :: OSI Approved :: MIT License` classifier. Before 2027, migrate to:

```toml
# In pyproject.toml
license = "MIT"               # SPDX expression string
```

and remove the `License :: OSI Approved :: MIT License` classifier from `classifiers`.
This has no effect on publishing today — builds and `twine check` both pass cleanly.

---

## Relevant Workflow Files

| Workflow | Trigger | Purpose |
|----------|---------|---------|
| `.github/workflows/release.yml` | Push of `v*` tag | Creates GitHub Release, dispatches PyPI publish |
| `.github/workflows/publish-pypi.yml` | Release published or manual dispatch | Builds, checks, and publishes to PyPI via OIDC |
| `.github/workflows/release-package.yml` | Release published | Builds standalone executables, attaches to Release |

---

## Troubleshooting

**`twine check` fails with "The description failed to render"**

The README must be valid reStructuredText or Markdown. Run:

```bash
pip install readme-renderer[md]
python -m readme_renderer README.md -o /dev/null
```

**OIDC token exchange fails in CI**

Ensure the `pypi` GitHub Environment exists and the Trusted Publisher is registered
on PyPI with the exact workflow filename (`publish-pypi.yml`) and environment name
(`pypi`).

**"File already exists" error on PyPI**

PyPI does not allow re-uploading the same version. Bump the version and rebuild
before retrying. For testing, use TestPyPI which allows more permissive re-uploads.

**Build includes unexpected files**

Check `MANIFEST.in` for explicit includes/excludes and ensure `.gitignore` patterns
do not accidentally include build artifacts in the sdist. Re-run:

```bash
python -m build --sdist 2>&1 | grep "adding"
```
