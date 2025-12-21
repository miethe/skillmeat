# Welcome to SkillMeat Beta!

Thank you for participating in the SkillMeat beta program. Your feedback will directly shape the final product and help us deliver an excellent tool for the Claude developer community.

This guide will get you set up and ready to test SkillMeat over the next 2-4 weeks.

## What is SkillMeat?

SkillMeat is a personal collection manager for Claude Code artifacts (Skills, Commands, Agents, MCP servers, Hooks). It enables developers to maintain, version, and deploy Claude artifacts across multiple projects with version control and marketplace integration.

**Current Beta Scope**: Skills, team collections, web interface, and MCP server management (Phases 0-4 complete).

## Getting Started

### Step 1: Installation

Choose one installation method:

**Option A: From PyPI (Beta Release)**
```bash
pip install skillmeat==0.3.0-beta.1
```

**Option B: From Source (Latest Development)**
```bash
git clone https://github.com/skillmeat/skillmeat.git
cd skillmeat
git checkout beta/v0.3.0

# Install with development dependencies
pip install -e ".[dev]"

# Or using uv (recommended for faster installs)
uv tool install --editable .
```

**Verify installation:**
```bash
skillmeat --version
# Should output: skillmeat 0.3.0-beta.1
```

### Step 2: Initial Configuration

```bash
# Initialize your collection
skillmeat init

# You'll be prompted to choose:
# - Default scope: user (global) or local (./.claude/)
# - GitHub token: Optional, required for private repos
```

**Configuration file**: `~/.skillmeat/config.toml`
```toml
[skillmeat]
default-scope = "user"
github-token = "ghp_xxxxxxxxxxxxxxxxxxxx"  # Optional
```

### Step 3: First Skills

**Add your first public skill:**
```bash
skillmeat add anthropics/skills/canvas-design
skillmeat list
```

**Add from your own repository:**
```bash
skillmeat add your-github-username/your-repo/path/to/skill
```

**Browse installed skills:**
```bash
skillmeat show canvas-design
```

### Step 4: Web Interface (Optional but Recommended)

SkillMeat includes a web interface for visual management:

```bash
# Start development server (http://localhost:3000)
skillmeat web dev

# Or production mode
skillmeat web start
```

**Key Features to Explore:**
- Browse and search your collection
- Deploy skills to scopes (user/local)
- Export/import bundles
- Team collaboration features
- MCP server management

### Step 5: Enable Usage Telemetry (Optional)

Help us improve SkillMeat by sharing anonymous usage metrics:

```bash
skillmeat config set telemetry-enabled true
```

**What we track:**
- Command usage frequency (which features you use)
- Error counts and types (to prioritize bug fixes)
- Installation/deployment times (for performance optimization)
- System info (OS, Python version, platform)

**What we DON'T track:**
- Skill names or content
- Personal information
- Passwords or API keys
- Private repository names

## Key Features to Test

Test these core features during beta and provide feedback:

### Collection Management
- [ ] **Add Skills**: `skillmeat add username/repo/path`
- [ ] **Remove Skills**: `skillmeat remove skill-name`
- [ ] **Update Skills**: `skillmeat update` and verify version resolution
- [ ] **List Skills**: `skillmeat list` with filtering by scope/tag
- [ ] **Show Details**: `skillmeat show skill-name` with full metadata

### Web Interface
- [ ] **Browse Collection**: View all installed skills with details
- [ ] **Search**: Find skills by name, tag, or description
- [ ] **Deploy**: Deploy skills to user or local scope
- [ ] **Import/Export**: Bundle skills for sharing with team

### Team Sharing
- [ ] **Export Bundle**: Export skills with `skillmeat export --format bundle`
- [ ] **Import Bundle**: Import team skills with `skillmeat import bundle.tar.gz`
- [ ] **Share Configuration**: Version control `.claude/skills.toml` in git repos

### MCP Server Management
- [ ] **List MCP Servers**: `skillmeat mcp list`
- [ ] **Deploy Server**: `skillmeat mcp deploy server-name`
- [ ] **Health Check**: `skillmeat mcp health` to verify server status
- [ ] **View Logs**: `skillmeat mcp logs server-name`

### Marketplace (Web UI)
- [ ] **Search**: Find skills by category or keyword
- [ ] **Install**: One-click installation to collection
- [ ] **View Ratings**: See community ratings and reviews
- [ ] **Publish** (optional): Share your own skills

## Providing Feedback

We value all feedback and have multiple channels depending on your preference:

### Report a Bug
Use GitHub Issues with these details:

1. **Steps to reproduce**: Exact commands you ran
2. **Expected behavior**: What should have happened
3. **Actual behavior**: What actually happened
4. **Environment**: OS, Python version, SkillMeat version
5. **Screenshots/logs**: Any error messages or unusual output

**Example:**
```
Title: "skillmeat add fails with permission error on Windows"

Steps to reproduce:
1. Run: skillmeat add anthropics/skills/canvas-design
2. Select scope: local
3. Observe error message

Expected: Skill installed successfully
Actual: Permission denied error on .claude/skills/

Environment:
- OS: Windows 11
- Python: 3.11.2
- SkillMeat: 0.3.0-beta.1
```

### Send General Feedback
Use any of these channels:

**1. GitHub Discussions** (Best for conversations)
- https://github.com/skillmeat/skillmeat/discussions
- Tag: `beta-feedback`
- Share ideas, ask questions, discuss features
- Public searchable archive

**2. In-App Feedback** (Quick notes)
```bash
skillmeat feedback "The web UI is confusing, needs better onboarding"
```
- Automatically includes system context
- Higher priority in support queue
- Sent directly to product team

**3. Weekly Office Hours** (Real-time discussion)
- **When**: Thursdays 2-3pm PT
- **Where**: Zoom link sent in welcome email
- **Agenda**: Q&A, demos, live troubleshooting
- **Recording**: Available after session

**4. Beta Feedback Form** (Structured feedback)
- Link: https://forms.skillmeat.dev/beta
- Detailed questions about specific features
- Usage metrics and satisfaction ratings
- Final survey at program end

### What We're Looking For

**Critical Issues** (Report immediately)
- Crashes or freezes
- Data loss or corruption
- Security vulnerabilities
- Platform-specific failures

**Bugs** (Report when discovered)
- Commands producing wrong output
- UI errors or broken interactions
- Performance problems
- Confusing error messages

**UX Issues** (Share observations)
- Confusing workflows or terminology
- Missing features that block your work
- Documentation gaps or errors
- Unexpected behavior

**Feature Requests** (Discuss and prioritize)
- Workflows not supported today
- Integrations with external tools
- Performance or scalability improvements

## Daily Tips for Beta Testing

1. **Try Different Workflows**: Don't just test happy paths
   - Try adding non-existent skills
   - Test with large collections (100+ skills)
   - Use both CLI and web interface
   - Test on different networks/VPNs

2. **Check Error Messages**: Are they clear and actionable?
   - Can you understand what went wrong?
   - Can you fix it with the error message alone?
   - Is the message in appropriate language?

3. **Verify Documentation**: Does docs match actual behavior?
   - Follow quickstart guide exactly
   - Try examples from docs
   - Check API documentation accuracy
   - Look for missing docs

4. **Monitor Performance**: Watch for slowness or resource usage
   - Time command execution
   - Check disk space usage
   - Monitor memory usage
   - Report unexpectedly slow operations

5. **Test Cross-Platform**: If you have access to multiple OS
   - Try Windows, macOS, and Linux
   - Report platform-specific issues
   - Check file path handling
   - Test shell integration

## Troubleshooting

### Installation Issues

**Issue**: `pip install skillmeat` fails
```bash
# Try updating pip first
pip install --upgrade pip

# Then install with verbose output
pip install -v skillmeat==0.3.0-beta.1
```

**Issue**: Command not found after install
```bash
# Check installation location
pip show skillmeat

# Add to PATH if needed
export PATH=$PATH:~/.local/bin

# Or reinstall with --user flag
pip install --user skillmeat
```

### Connection Issues

**Issue**: GitHub API rate limit exceeded
```bash
# Add GitHub token for higher limits
skillmeat config set github-token YOUR_GITHUB_TOKEN

# Or create token: https://github.com/settings/tokens/new
# Scopes needed: repo (all), read:user
```

**Issue**: Cannot clone private repositories
```bash
# Ensure GitHub token is configured
skillmeat config get github-token

# Token must have 'repo' scope
```

### Web Interface Issues

**Issue**: Web UI fails to start
```bash
# Check if port 3000 is in use
lsof -i :3000

# Use different port
skillmeat web dev --port 3001
```

## Staying in Touch

- **Slack Channel**: #skillmeat-beta (get link in welcome email)
- **Status Page**: updates.skillmeat.dev
- **Email Updates**: Weekly beta program updates to your inbox
- **Twitter**: @skillmeat_dev for announcements

## Reward and Recognition

As a beta participant, you'll receive:

- **Early Access**: v1.0 release 2 weeks before general availability
- **Contributor Badge**: Special badge on marketplace profile
- **Release Notes Credit**: Your name/organization in v1.0 release notes
- **Optional Swag**: SkillMeat t-shirt, stickers, and laptop case
- **Priority Support**: 24-hour response time for your issues

## Code of Conduct

Beta participants agree to:

- Respect other participants and the development team
- Keep unreleased features confidential
- Provide constructive feedback (even if critical)
- Report security issues privately to security@skillmeat.dev
- Use beta features for testing only, not production

## Still Have Questions?

- **FAQ**: https://docs.skillmeat.dev/beta-faq
- **Docs**: https://docs.skillmeat.dev
- **Discussions**: https://github.com/skillmeat/skillmeat/discussions
- **Email**: beta-support@skillmeat.dev

---

**Thank you for being part of SkillMeat's journey to GA!**

Your feedback makes SkillMeat better for everyone. Happy testing!

**Next Step**: Follow Steps 1-5 above to get set up, then join us at Thursday office hours to ask any questions.
