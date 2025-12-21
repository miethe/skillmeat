# SkillMeat Beta Program

Welcome to the beta program documentation hub. This directory contains all materials for planning, executing, and analyzing the SkillMeat closed beta program before general availability release.

## Quick Links

### For Beta Participants
- **[Getting Started](beta-onboarding.md)** - Installation, setup, and first steps
- **[Feedback Form](feedback-template.md)** - How and where to provide feedback
- **[Troubleshooting](beta-onboarding.md#troubleshooting)** - Common issues and solutions

### For Program Admins
- **[Program Plan](beta-program-plan.md)** - Timeline, objectives, success criteria
- **[Support Guide](support-guide.md)** - Daily/weekly tasks, communication templates
- **[Invitation Email](participant-invitation-email.md)** - Recruiting and onboarding

### For Analysis & Reporting
- **[Telemetry Dashboard](beta-telemetry.md)** - Real-time metrics and monitoring
- **[Post-Beta Survey](post-beta-survey.md)** - Final feedback collection
- **[Feedback Analysis Script](../scripts/analyze_beta_feedback.py)** - Automated analysis

---

## Program Overview

### What We're Testing
SkillMeat v0.3.0-beta.1 with completed features from Phases 0-4:
- Collection management and artifact organization
- Skill installation, versioning, and deployment
- Web interface for visual management
- Team collaboration (export/import bundles)
- MCP server management
- Marketplace integration (search, install, publish)
- Cross-platform support (macOS, Linux, Windows)

### Who's Involved
**Target**: 20-30 beta testers across:
- Skill Developers (40%)
- Team Leads (30%)
- Individual Users (30%)

**Platforms**: macOS (40%), Linux (30%), Windows (30%)

### Timeline
- **Week 1**: Participant recruitment, invitations, onboarding
- **Week 2-3**: Active testing, daily issue monitoring
- **Week 4**: Feedback collection and analysis
- **Week 5**: Bug fixes and iterations
- **Week 6**: Final validation, GA readiness assessment

### Success Criteria
All of these must be met for GA release:
- [ ] 80% participant completion rate
- [ ] 4.0+ average satisfaction (1-5 scale)
- [ ] Zero P0/P1 bugs unresolved
- [ ] 4.0+ documentation clarity rating
- [ ] 100% of feedback categorized and addressed
- [ ] <1% cross-platform crash rate
- [ ] P95 API response time <100ms

---

## Getting Started as a Program Admin

### 1. Pre-Beta Phase (Week -1)

**Setup Infrastructure**
```bash
# Start observability stack for telemetry
docker-compose -f docker-compose.observability.yml up -d

# Verify Grafana dashboard is accessible
open http://localhost:3001
```

**Prepare Materials**
- [ ] Review and customize all templates in this directory
- [ ] Create Google Form for feedback (use `feedback-template.md` as base)
- [ ] Create Airtable base for participant tracking
- [ ] Set up Slack channel (#skillmeat-beta)
- [ ] Create GitHub Discussion board (beta-feedback label)
- [ ] Prepare invitations (customize `participant-invitation-email.md`)

**Recruit Participants**
- [ ] Identify 20-30 candidates across roles and platforms
- [ ] Create participants.csv with name, email, role, platform
- [ ] Run dry-run: `python scripts/send_beta_invitations.py --file participants.csv --dry-run`
- [ ] Send real invitations: `python scripts/send_beta_invitations.py --file participants.csv`

### 2. Week 1: Onboarding

**Track Participant Status**
- [ ] Monitor signup form responses
- [ ] Add confirmed participants to Airtable
- [ ] Send follow-up email (see `participant-invitation-email.md`)
- [ ] Add to Slack channel and GitHub access

**Support Participants**
- [ ] Send onboarding materials
- [ ] Host optional setup help session
- [ ] Prepare for office hours (Thursday 2-3pm PT)

### 3. Week 2-3: Active Testing

**Daily** (30 min):
- [ ] Check telemetry dashboard for anomalies
- [ ] Monitor GitHub Discussions and Slack
- [ ] Triage new bugs and feature requests
- [ ] Acknowledge all new issues within 24 hours

**Weekly** (2 hours):
- [ ] Engagement check - identify inactive participants
- [ ] Triage and categorize feedback
- [ ] Host office hours (Thursday 2-3pm PT)
- [ ] Send status email to participants

### 4. Week 4: Feedback Collection

**Process Feedback**
- [ ] Compile all feedback from multiple channels into JSON format
- [ ] Run analysis: `python scripts/analyze_beta_feedback.py`
- [ ] Share report with engineering team

**Send Surveys**
- [ ] Send post-beta survey (use `post-beta-survey.md`)
- [ ] Send reminders (3 days before, 1 day before deadline)
- [ ] Track completion rate

### 5. Week 5-6: Final Validation

**Bug Resolution**
- [ ] Ensure all P0/P1 bugs are resolved
- [ ] Update participants on fix status daily
- [ ] Verify fixes in staging

**GA Readiness**
- [ ] Review survey results
- [ ] Check all success criteria met
- [ ] Make go/no-go decision
- [ ] Prepare GA announcement

**Thank Participants**
- [ ] Send thank you emails
- [ ] Confirm swag shipment
- [ ] Share release notes credit
- [ ] Conduct team retrospective

---

## File Organization

### Participant-Facing Documents
- `beta-onboarding.md` - Complete setup and testing guide
- `feedback-template.md` - Structured feedback form
- `participant-invitation-email.md` - Invitation and follow-up emails
- `post-beta-survey.md` - Final survey with analysis framework

### Admin & Team Documents
- `beta-program-plan.md` - Program objectives, timeline, success criteria
- `support-guide.md` - Daily/weekly procedures and communication templates
- `beta-telemetry.md` - Monitoring, dashboards, alerts

### Scripts
- `../scripts/analyze_beta_feedback.py` - Analyze feedback and generate report
- `../scripts/send_beta_invitations.py` - Manage invitation campaign

---

## Communication Workflow

### Feedback Channels
```
Participant
    ├─ GitHub Discussions → async, searchable, technical discussion
    ├─ Slack #skillmeat-beta → real-time, quick questions
    ├─ In-app feedback → direct integration with telemetry
    ├─ Email → structured bug reports
    └─ Office hours → live troubleshooting (Thursday 2-3pm PT)
         ↓
  Support Team
    ├─ Triage and categorize
    ├─ Assign to engineering
    ├─ Track in Airtable
    └─ Respond to participant
         ↓
  Engineering
    ├─ Reproduce issue
    ├─ Assign priority (P0-P3)
    ├─ Fix and test
    └─ Update participant
```

### Response SLAs
| Issue Type | Response | Fix Target |
|-----------|----------|-----------|
| P0 (Critical) | 15 min | 4 hours |
| P1 (High) | 1 hour | 24 hours |
| P2 (Medium) | 4 hours | 1 week |
| P3 (Low) | 24 hours | 2+ weeks |

---

## Key Metrics to Monitor

### Daily
- **DAU (Daily Active Users)**: Target >70% by Week 3
- **Error Rate**: Target <1%
- **P0 Bugs Open**: Target 0 (immediate escalation if >0)

### Weekly
- **Completion Rate**: Target >80% overall
- **Average Satisfaction**: Target >4.0 (on 1-5 scale)
- **Feature Adoption**: Target >70% for core features

### End of Beta
- **NPS Score**: Target >30
- **Overall Satisfaction**: Target >4.0
- **Blocker Bugs**: Target 0
- **Documentation Clarity**: Target >4.0
- **Crash Rate**: Target <0.5%

---

## Troubleshooting Guide

### Participant Issues

**Issue**: Can't install SkillMeat
- **Solution**: Check Python version (3.9+), pip up-to-date
- **Reference**: `beta-onboarding.md#installation-issues`

**Issue**: GitHub API rate limit exceeded
- **Solution**: Provide GitHub token
- **Reference**: `beta-onboarding.md#connection-issues`

**Issue**: Web interface fails to start
- **Solution**: Check port 3000 available, try different port
- **Reference**: `beta-onboarding.md#web-interface-issues`

### Program Issues

**Issue**: Low participation/engagement
- **Solution**: 1-on-1 check-ins, identify blockers, send re-engagement messages
- **Reference**: `support-guide.md#participant-engagement-check`

**Issue**: High bug volume
- **Solution**: Prioritize by severity, batch fixes, communicate progress
- **Reference**: `beta-program-plan.md#risk-mitigation`

**Issue**: Platform-specific failures
- **Solution**: Assign to platform expert, may require targeted investigation
- **Reference**: `beta-telemetry.md#platform-specific-issues`

---

## Documentation Structure

### Phases of Beta Program

**Phase 1: Recruitment & Onboarding (Week 1)**
- Document: `participant-invitation-email.md`
- Script: `../scripts/send_beta_invitations.py`
- Owner: Program Manager, Dev Relations

**Phase 2: Active Testing (Week 2-3)**
- Document: `beta-onboarding.md`
- Reference: `support-guide.md` (daily/weekly tasks)
- Owner: Support Team, Engineering

**Phase 3: Feedback Collection (Week 4)**
- Document: `post-beta-survey.md`
- Form: `feedback-template.md`
- Script: `../scripts/analyze_beta_feedback.py`
- Owner: Program Manager, Product

**Phase 4: Analysis & Iteration (Week 5)**
- Document: `beta-program-plan.md` (metrics tracking)
- Document: `beta-telemetry.md` (monitoring)
- Owner: Engineering, Product Manager

**Phase 5: GA Readiness (Week 6)**
- Deliverable: Feedback report
- Deliverable: Go/no-go decision
- Deliverable: Release announcement
- Owner: Product Manager, Executive Team

---

## Tools & Infrastructure

### Email
- **Service**: SendGrid, AWS SES, or similar
- **Account**: beta-program@skillmeat.dev
- **Templates**: Customizable in invitation email doc

### Forms & Surveys
- **Feedback Form**: Google Forms (or Typeform)
- **Post-Beta Survey**: Google Forms (or Qualtrics)
- **Signup Form**: Google Forms (or Notion)

### Databases
- **Participant Tracking**: Airtable or Google Sheets
- **Feedback Storage**: `docs/user/beta/feedback/` directory
- **Invitation Tracking**: `docs/user/beta/invitation-tracking.json`

### Communication
- **Real-time**: Slack (#skillmeat-beta, #skillmeat-dev)
- **Async**: GitHub Discussions, Email
- **Video**: Zoom (office hours, pair debugging)

### Monitoring
- **Metrics**: Prometheus + Grafana (http://localhost:3001)
- **Logs**: Loki (log aggregation and search)
- **Status**: Custom dashboard with real-time metrics

---

## Best Practices

### Participant Communication
1. **Be responsive**: Acknowledge all issues within 24 hours
2. **Be transparent**: Share status and blockers openly
3. **Be appreciative**: Thank participants for time and feedback
4. **Be honest**: Admit when you don't know, commit to finding out

### Feedback Management
1. **Categorize immediately**: Don't let feedback pile up unreviewed
2. **Deduplicate**: Combine similar reports to avoid count distortion
3. **Prioritize data-driven**: Use frequency, severity, platform impact
4. **Communicate prioritization**: Explain why some issues fixed first

### Issue Tracking
1. **Single source of truth**: All issues in GitHub Issues
2. **Label consistently**: Use labels for triage (beta-feedback, platform tags)
3. **Link to participant**: Cross-reference participant ID or name
4. **Close with resolution**: Always update participant when fixed

### Metrics & Reporting
1. **Daily standups**: 5-min metric review
2. **Weekly reports**: Email to participants
3. **Real-time dashboards**: Grafana for team monitoring
4. **Final report**: Comprehensive analysis for decision-making

---

## FAQ

**Q: Can we include people who've used SkillMeat before?**
A: Yes, but note that in feedback form. Fresh users provide better UX feedback.

**Q: What if we don't meet success criteria?**
A: Delay GA, address critical issues, run mini beta round 2.

**Q: How do we handle confidentiality?**
A: Beta features are confidential until GA. Include NDA in invitation.

**Q: Can beta participants request features for post-GA?**
A: Yes! Track in separate "Post-GA Backlog" column in Airtable.

**Q: How do we prevent feature requests from derailing GA?**
A: Clearly communicate: GA = Phases 0-4 only. Post-GA = new features.

---

## Success Stories

After beta program completes successfully:
- Publish blog post with retrospective
- Thank participants publicly
- Share key learnings
- Showcase featured use cases
- Announce GA with confidence

---

## Contact & Support

**Questions about beta program?**
- Program Manager: [name] (slack: @[handle])
- Support Email: beta-support@skillmeat.dev
- Discussions: https://github.com/skillmeat/skillmeat/discussions

**Documentation Updates**
- Issues with docs: Post in GitHub Discussions with `beta-feedback` label
- Suggestions for improvement: Reply directly to this file's discussion

---

## Version History

- **v1.0** - Initial beta program documentation (2024-11-17)
- **v0.9** - Draft (2024-11-15)

---

**Last Updated**: 2024-11-17
**Status**: Ready for Phase 1 (Recruitment)
**Next Review**: Week 1 of beta program
