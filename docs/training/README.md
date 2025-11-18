---
title: SkillMeat Training & Enablement
description: Comprehensive training resources, learning paths, and onboarding materials for SkillMeat users
audience: developers, users, trainers
tags:
  - training
  - onboarding
  - learning
  - enablement
created: 2025-11-17
updated: 2025-11-17
category: Training
status: Published
related:
  - onboarding-script.md
  - ../guides/web-ui-guide.md
  - ../guides/team-sharing-guide.md
  - ../guides/mcp-management.md
  - ../guides/marketplace-usage-guide.md
---

# SkillMeat Training & Enablement

Welcome to SkillMeat training materials! This section provides resources for learning SkillMeat at your own pace or in structured training sessions.

## Training Paths

Choose the learning path that matches your role and experience level.

### For Individual Users

**Goal**: Learn to manage your Claude artifacts locally

**Duration**: 1 hour

**Learning path**:
1. [Quick Start Guide](../guides/quickstart.md) (5 min) - Installation and first steps
2. [Collections Management](../guides/collections-guide.md) (15 min) - Creating and managing collections
3. [Web Interface Tutorial](#web-interface-tutorial) (20 min) - Using the web UI
4. [Marketplace Basics](#marketplace-basics) (15 min) - Browsing and installing artifacts

**What you'll learn**:
- How to initialize a collection
- How to add and manage artifacts
- How to deploy to projects
- How to browse the marketplace
- How to use the web interface

**Success criteria**:
- Can initialize a collection
- Can add an artifact from GitHub
- Can deploy an artifact to a project
- Can navigate web interface
- Can search marketplace

---

### For Team Leads

**Goal**: Learn to share and manage artifacts across your team

**Duration**: 2-2.5 hours

**Learning path**:
1. Individual user path (1 hour)
2. [Team Sharing Tutorial](./team-sharing-tutorial.md) (30 min) - Export, import, merge strategies
3. [Vault Configuration Guide](./vault-setup.md) (20 min) - Set up Git or S3 vault
4. [Team Best Practices](./team-best-practices.md) (20 min) - Governance and workflows

**What you'll learn**:
- How to export collections as bundles
- How to set up team vaults (Git or S3)
- How to manage conflicts and merges
- How to establish team policies
- How to track usage and changes

**Success criteria**:
- Can export a collection as bundle
- Can import a bundle from teammate
- Can resolve conflicts intelligently
- Can configure team vault
- Can guide team through workflows

---

### For Developers/Publishers

**Goal**: Learn to create and publish artifacts to marketplace

**Duration**: 3-3.5 hours

**Learning path**:
1. Team lead path (2-2.5 hours)
2. [Creating Artifacts Guide](./creating-artifacts.md) (30 min) - Build skills, commands, agents
3. [Publishing Guide](../guides/publishing-to-marketplace.md) (30 min) - Publish to marketplace
4. [Security Best Practices](./security-practices.md) (20 min) - Keep artifacts secure

**What you'll learn**:
- How to structure artifacts properly
- How to add metadata and documentation
- How to package for publishing
- How to manage versions
- How to monitor usage
- How to handle security responsibly

**Success criteria**:
- Can create a new artifact
- Can package it properly
- Can publish to marketplace
- Can manage versions
- Can interpret usage analytics

---

### For Administrators/DevOps

**Goal**: Learn to manage SkillMeat infrastructure and operations

**Duration**: 3.5-4 hours

**Learning path**:
1. Team lead path (2-2.5 hours)
2. [MCP Administration](./mcp-admin-tutorial.md) (30 min) - Deploy and manage MCP servers
3. [Marketplace Operations](../runbooks/marketplace-operations.md) (30 min) - Run marketplace
4. [Observability & Monitoring](./observability-tutorial.md) (30 min) - Monitor and debug
5. [Security Operations](./security-operations.md) (20 min) - Security hardening

**What you'll learn**:
- How to deploy MCP servers
- How to monitor system health
- How to interpret metrics and logs
- How to respond to alerts
- How to harden security
- How to manage marketplace operations

**Success criteria**:
- Can deploy MCP server
- Can monitor health checks
- Can interpret Prometheus metrics
- Can use Grafana dashboards
- Can respond to security incidents
- Can manage marketplace vaults

---

### For Support Team

**Goal**: Learn to help users troubleshoot issues

**Duration**: 4-5 hours

**Learning path**:
1. Individual user path (1 hour)
2. All team lead, developer, and admin paths (combined 8 hours)
3. [Support Scripts and Scenarios](./support-scripts/) (30 min) - Review common issues
4. [Troubleshooting Guide](../guides/troubleshooting.md) (30 min) - Debug techniques
5. [Support Best Practices](./support-best-practices.md) (20 min) - Communication and escalation

**What you'll learn**:
- How to replicate user issues
- How to use diagnostic commands
- How to interpret error messages
- How to guide users through solutions
- How to escalate to engineering
- How to document solutions

**Success criteria**:
- Can troubleshoot 80% of common issues
- Can replicate most user problems
- Can interpret logs and metrics
- Can guide users through solutions
- Can effectively escalate

---

## Core Learning Resources

### Quick Start Guide
**Time**: 5 minutes
**Level**: Beginner
**Goal**: Get SkillMeat running in 5 minutes

**Topics**:
- Installation
- Initialization
- First artifact
- First deployment

See: [Quick Start](../guides/quickstart.md)

---

### Video Tutorials (Described)

These tutorials are described for accessibility:

#### Getting Started (5 min)
Topics: Installation, creating collection, adding first artifact

**Description**: A walkthrough of initial setup showing the `skillmeat init` command, `skillmeat add` with a GitHub spec, and verifying with `skillmeat list`.

#### Web Interface Tour (10 min)
Topics: Dashboard, collections, artifacts, deploy, analytics

**Description**: Demo of the web interface showing the collections dashboard, artifact detail drawer, deploy UI, and analytics widgets. Shows real-time sync progress with SSE indicators.

#### Team Sharing (15 min)
Topics: Export bundles, import, merge strategies, conflict resolution

**Description**: Step-by-step export of collection, sharing via Git, teammate importing with conflict resolution, using the merge/fork/skip strategies.

#### Publishing (20 min)
Topics: Create bundle, add metadata, validate, submit to marketplace

**Description**: Creating new artifact, adding YAML metadata, structuring for distribution, running security checks, publishing to marketplace.

#### MCP Management (15 min)
Topics: Add server, deploy, configure, health monitoring

**Description**: Adding MCP server from GitHub, deploying to Claude with `mcp deploy`, configuring environment variables, checking health status.

---

### Written Tutorials

#### Web Interface Tutorial
**Time**: 20 minutes
**Level**: Beginner-Intermediate
**Path**: Individual users, team leads

Detailed guide covering:
- Dashboard overview and navigation
- Searching and filtering collections
- Viewing artifact details
- Deploying artifacts
- Real-time progress monitoring
- Analytics dashboard
- Keyboard shortcuts

---

#### Team Sharing Tutorial
**Time**: 30 minutes
**Level**: Intermediate
**Path**: Team leads, developers, admins

Detailed guide covering:
- Exporting collections as bundles
- Bundle security (signing, verification)
- Importing bundles
- Merge strategies (merge, fork, skip)
- Conflict resolution
- Vault setup (Git, S3)
- Best practices for teams

---

#### MCP Administration Tutorial
**Time**: 30 minutes
**Level**: Intermediate-Advanced
**Path**: Admins, DevOps

Detailed guide covering:
- Understanding MCP servers
- Adding servers to collection
- Deployment process
- Environment configuration
- Health monitoring
- Log interpretation
- Troubleshooting deployments
- Platform-specific considerations

---

#### Observability Tutorial
**Time**: 30 minutes
**Level**: Intermediate-Advanced
**Path**: Admins, DevOps, ops engineers

Detailed guide covering:
- Prometheus metrics overview
- Grafana dashboard navigation
- Common metrics and their meaning
- Setting up alerts
- Interpreting logs
- Distributed tracing
- Performance troubleshooting
- Capacity planning

---

## Cheat Sheets

Quick reference guides for common tasks:

### CLI Commands Reference
**File**: `./cli-cheat-sheet.md`

Quick lookup for:
- Collection commands
- Artifact commands
- Deployment commands
- MCP commands
- Marketplace commands
- Analytics commands
- Configuration commands

---

### Web UI Shortcuts
**File**: `./web-ui-shortcuts.md`

Keyboard shortcuts and UI shortcuts:
- Navigation shortcuts
- Search shortcuts
- Common workflows
- Accessibility features

---

### Common Workflows
**File**: `./common-workflows.md`

Step-by-step guides for:
- Onboarding new team member
- Publishing new artifact
- Installing team bundle
- Deploying MCP server
- Troubleshooting deployment
- Updating artifact
- Rolling back changes

---

## Support Scripts

Common support scenarios with solutions:

### Support Scripts Directory
**Location**: `./support-scripts/`

Available scripts:
- `password-reset.md` - Reset authentication token
- `collection-recovery.md` - Recover corrupted collection
- `marketplace-error.md` - Resolve marketplace issues
- `mcp-deployment-issue.md` - Debug MCP deployment
- `bundle-import-failure.md` - Resolve import errors
- `web-ui-troubleshooting.md` - Fix web interface issues
- `performance-issues.md` - Diagnose slow operations

---

## Training Delivery

### Self-Paced Learning

Users can complete training at their own pace using written guides and tutorials.

**Typical timeline**:
- Individual user path: 1-2 hours
- Team lead path: 2-4 hours
- Developer path: 3-6 hours
- Admin path: 4-8 hours

---

### Instructor-Led Training

Facilitated training sessions using the onboarding script.

**Session structure**:
1. Introduction (5 min)
2. First collection walkthrough (10 min)
3. Web interface demo (10 min)
4. Marketplace overview (5 min)
5. Q&A and hands-on (5 min)

**Duration**: 30-40 minutes depending on group
**Recommended size**: 10-20 people
**Setup**: Users need SkillMeat installed

See [Onboarding Script](./onboarding-script.md) for facilitation guide.

---

### One-on-One Onboarding

Personalized training for individual team members.

**Structure**:
1. Assess current knowledge
2. Follow appropriate learning path
3. Hands-on setup and testing
4. Q&A and troubleshooting
5. Follow-up resources

**Duration**: 30-60 minutes depending on role

---

## Support Team Training

### Support Agent Onboarding

Checklist for onboarding new support team members:

- [ ] Complete all learning paths (16+ hours)
- [ ] Review all documentation in `/docs`
- [ ] Practice common troubleshooting scenarios
- [ ] Shadow experienced support agent (1 week)
- [ ] Handle supervised support requests (2 weeks)
- [ ] Independent support and escalation (ongoing)

### Support Best Practices

Key principles for support:
- Replicate user issue before escalating
- Use diagnostic tools (check command, logs, metrics)
- Provide clear step-by-step guidance
- Document solutions for future reference
- Escalate to engineering when needed
- Follow up on complex issues

See: [Support Best Practices](./support-best-practices.md)

---

## Feedback and Improvement

### Training Feedback

Help us improve training materials:

**Feedback form**: [Training Feedback](https://forms.skillmeat.dev/training-feedback)

**Topics to cover**:
- Clarity of instructions
- Completeness of guides
- Pace and difficulty
- Suggestions for improvement
- Missing topics

### Community Resources

Get help from the community:

- **GitHub Discussions**: https://github.com/miethe/skillmeat/discussions/categories/training
- **Community Chat**: [Slack/Discord]
- **Office Hours**: Thursdays 2-3pm PT

---

## Trainer Resources

### How to Deliver Training

Best practices for facilitating SkillMeat training:

1. **Prepare environment**
   - Ensure all participants have SkillMeat installed
   - Have sample collections ready
   - Test web interface and marketplace access

2. **Engage learners**
   - Encourage hands-on practice
   - Answer questions throughout
   - Adapt pace to group needs

3. **Follow structure**
   - Use onboarding script for consistency
   - Allocate time for Q&A
   - Provide written materials as reference

4. **Gather feedback**
   - Send feedback form after training
   - Note common questions for future improvement
   - Track training effectiveness

See: [Trainer Guide](./trainer-guide.md)

---

## Learning Outcomes by Role

### Individual Users
After training, you will be able to:
- Initialize and manage a collection
- Add artifacts from GitHub and local sources
- Deploy artifacts to Claude Code projects
- Browse and use the web interface
- Search the marketplace
- Troubleshoot basic issues

### Team Leads
After training, you will be able to:
- Export collections for team sharing
- Import and merge team bundles
- Set up team vaults (Git or S3)
- Guide team through workflows
- Track team artifact usage
- Establish governance policies

### Developers
After training, you will be able to:
- Create new artifacts
- Add proper metadata
- Package for marketplace
- Publish and manage versions
- Monitor usage metrics
- Implement security best practices

### Administrators
After training, you will be able to:
- Deploy and manage MCP servers
- Monitor system health
- Interpret metrics and logs
- Respond to alerts
- Manage marketplace operations
- Harden security

---

## Next Steps

1. **Identify your role** - Which path matches your needs?
2. **Allocate time** - Block time for training
3. **Set up environment** - Install SkillMeat and prerequisites
4. **Complete learning path** - Follow guides in order
5. **Practice** - Apply knowledge with sample projects
6. **Get support** - Ask questions in GitHub Discussions

---

## Resources Summary

| Resource | Time | Level | Audience |
|----------|------|-------|----------|
| Quick Start | 5 min | Beginner | Everyone |
| Web UI Tutorial | 20 min | Beginner | Users, Leads |
| Team Sharing Tutorial | 30 min | Intermediate | Leads, Devs |
| MCP Admin Tutorial | 30 min | Intermediate | Admins |
| Observability Tutorial | 30 min | Intermediate | Admins |
| CLI Cheat Sheet | Reference | All | Everyone |
| Support Scripts | Reference | All | Support Team |

---

**Questions?** Check [FAQ](../faq.md) or ask in [GitHub Discussions](https://github.com/miethe/skillmeat/discussions)
