# Beta Program Support Guide

For SkillMeat beta program administrators and support team.

## Overview

This guide provides operational procedures for running the SkillMeat closed beta program, managing participant communications, and responding to feedback and issues.

**Support Team Roles:**
- **Program Manager**: Oversees timeline, participant management, communications
- **Developer Relations**: Hosts office hours, responds to questions in discussions
- **Engineering**: Triages bugs, implements fixes, updates participants on progress
- **Documentation**: Updates docs based on feedback, clarifies unclear areas

## Participant Management

### Adding Participants

**Process for enrolling new beta participants:**

1. **Recruitment**
   - Target 20-30 participants across roles and platforms
   - Use invite tracking spreadsheet (shared in Slack)
   - Diversity matters: 40% skill developers, 30% team leads, 30% individual users

2. **Invitation**
   - Send from: beta-program@skillmeat.dev
   - Template: `docs/user/beta/participant-invitation-email.md`
   - Include personalized greeting when possible
   - Set expectations clearly (2-week active testing, 10-15 min/day commitment)

3. **Enrollment**
   - Participant completes signup form (Google Form link in email)
   - Add to beta participants database (Airtable)
   - Add to Slack channel (#skillmeat-beta)
   - Confirm receipt of onboarding materials

### Tracking Participant Status

Use shared Airtable base: `SkillMeat Beta Participants`

**Columns to maintain:**
- Name, Email, Organization, Role, Platform
- Signup date, Installation date, Last active date
- Status (Onboarded, Active, Inactive, Churned)
- Feedback submitted (Yes/No), Survey complete (Yes/No)
- Notes (issues encountered, special requests, etc.)

**Weekly status review:**
- Mark inactive participants (no activity 3+ days)
- Send gentle re-engagement message to inactive users
- Update status before weekly standup

## Daily Tasks (30 min)

Perform these every working day during beta period:

- [ ] **Check Telemetry Dashboard** (5 min)
  - Review Overview dashboard for anomalies
  - Check error rate spike, any P0 alerts?
  - Note DAU and overall health status

- [ ] **Monitor GitHub Discussions** (10 min)
  - Sort by recent activity
  - Read new issues/questions (filter: `is:open label:beta-feedback`)
  - Mark critical issues with `priority-high`
  - Acknowledge all new issues with template response

- [ ] **Review Slack #skillmeat-beta** (10 min)
  - Read new messages
  - Answer questions (or tag appropriate team member)
  - Note recurring issues for discussion

- [ ] **Check Support Email** (5 min)
  - Inbox: beta-support@skillmeat.dev
  - Respond to issues within 24 hours
  - Forward bugs to #skillmeat-dev for triage

## Weekly Tasks (2 hours)

Perform these weekly (typically Monday morning):

### 1. Participant Engagement Check (30 min)

```bash
# Run Airtable query to check status
airtable view "Beta Participants" filter "Last active < 3 days"
```

**Actions:**
- For inactive >3 days: Send re-engagement message via Slack
  - "Hi [name]! Haven't heard from you in a few days. Any blockers or issues?"
  - Offer help session or pair debugging

- For inactive >7 days: Schedule 1-on-1 call
  - "Would love to chat about your experience so far"
  - Identify blockers and address them
  - Offer incentives for completion (swag, early access, etc.)

- For churned participants: Send exit survey
  - "We noticed you've stepped back. Quick feedback on why?"
  - Link to short 2-minute survey

### 2. Feedback Collection and Triage (45 min)

**Process:**
1. Download new feedback from Google Forms
2. Export to CSV: `feedback_YYYY-MM-DD.csv`
3. Upload to shared folder: `/feedback/raw/`
4. Parse into JSON format:
   ```json
   {
     "participant_id": "user123",
     "submitted_at": "2024-11-21T14:30:00Z",
     "platform": "macos",
     "role": "skill_developer",
     "satisfaction_ratings": { ... },
     "bugs": [ ... ],
     "feature_requests": [ ... ]
   }
   ```
5. Store in `docs/user/beta/feedback/` directory
6. Run analysis script: `python scripts/analyze_beta_feedback.py`

**Triage bugs:**
- Assign severity (P0/P1/P2/P3)
- Assign to engineer
- Create GitHub issue if not already filed
- Update issue label with `beta-feedback`

**Triage features:**
- Assign priority (High/Medium/Low)
- Discuss in weekly planning meeting
- Respond to participant with status

### 3. Weekly Office Hours (30 min)

**Schedule:** Thursday 2-3pm PT

**Preparation:**
1. Prepare agenda (email to team 24 hours before)
2. Create Zoom link and send to participants (in advance)
3. Prepare demo of any new fixes or features
4. Have top 3 issues ready to discuss

**Facilitation:**
- Welcome and thanks (~1 min)
- Quick wins/updates from engineering (~5 min)
- Q&A from participants (~15 min)
- Feature demo or deep dive (~7 min)
- Ask for feedback and sign off (~2 min)

**Recording:**
- Record and upload to shared drive
- Post link in #skillmeat-beta Slack
- Create transcript for accessibility

### 4. Weekly Status Report (15 min)

Draft weekly email to participants (send Thursday EOD):

```
Subject: SkillMeat Beta Week 2 Update

Hi everyone,

Great progress this week! Here's what happened:

**Metrics**
- DAU: 24/28 (85%)
- Avg satisfaction: 4.2/5
- New bugs reported: 3 (all triaged and assigned)

**Accomplishments**
- Fixed CLI color output issue on Windows
- Added batch import feature requested by 3+ participants
- Updated documentation on MCP setup

**In Progress**
- Working on slow export performance issue
- Improving error messages (top feedback item)
- Marketplace search optimization

**Coming Next**
- Team collaboration improvements (2 participants requested)
- Better progress reporting in web UI
- Documentation refresh based on questions

**Known Issues**
- Windows path handling in some edge cases (P2 - workaround available)
- Marketplace search showing stale results (P1 - fix in progress)

**Next Office Hours**
Thursday 2-3pm PT - See you there!

Thanks for your feedback and testing,
SkillMeat Team
```

## Responding to Feedback

### Bug Report Response Template

**Initial acknowledgment** (within 24 hours):
```
Thanks for reporting this! We've received your report:

**Issue**: [Brief title]
**Severity**: [P0/P1/P2/P3]
**Status**: Triaged and assigned

We'll keep you updated on progress. If you have a workaround in the meantime,
feel free to use it.
```

**Progress update** (if bug not fixed within 48 hours):
```
**Update on [Issue]**

We're actively working on this. Engineering says [brief status].

ETA: [fixed by Friday / early next week / not clear yet]

Thanks for your patience!
```

**Resolution notification**:
```
**FIXED: [Issue]**

Good news! We've fixed this issue. It's available in the latest build.

To update: `pip install --upgrade skillmeat`

Please test and let us know if it resolves your issue. If you hit any problems,
reply to this thread.
```

### Feature Request Response Template

**High Priority Requests**:
```
Great idea! We've added this to our roadmap for [version/timeline].

**Use case**: [Summarize why this matters]
**Priority**: High
**Target release**: [timeframe]

We'll keep you in the loop on progress.
```

**Medium/Low Priority Requests**:
```
Thanks for the suggestion. We've added this to our backlog.

**Why this matters**: [Summarize use case]
**Priority**: [Medium/Low]
**Next review**: [timeframe]

We'll revisit prioritization after gathering more feedback from participants.
```

### Documentation Issues Response

```
Thanks for pointing this out! You're right - [description of issue].

**What we'll fix**: [List items to clarify]
**Timeline**: Updated by [day]
**Affected docs**: [List pages]

We appreciate you catching this!
```

## Escalation Procedures

### P0 Bug Escalation

**Immediate actions:**
1. Page on-call engineer right away (Slack message)
2. Post in #skillmeat-dev channel
3. Create high-priority GitHub issue
4. Update all participants about issue

**Communication to participants:**
```
[ALERT] Service Issue

We've identified an issue affecting [feature].

Status: Engineers investigating
ETA: Fix within [timeframe]

Workaround: [if available]

We'll update you every 30 minutes.
```

### P1 Bug Escalation

**Daily standup item:**
1. Add to engineering daily standup
2. Ensure engineer assigned and making progress
3. Check daily for status updates
4. Communicate progress to reporter

### Feature Request Escalation

**Weekly planning meeting:**
1. Compile all feature requests by frequency
2. Discuss priority with product/engineering
3. Decide on roadmap impact
4. Communicate decisions to participants

## Issue Triage Matrix

| Severity | Criteria | Response SLA | Fix SLA | Resolution |
|----------|----------|--------------|---------|-----------|
| **P0** | Crash, data loss, security | 15 min | 4 hours | Hotfix release |
| **P1** | Core feature broken, impacts 5+ users | 1 hour | 24 hours | Next release |
| **P2** | Feature works with workaround | 4 hours | 1 week | Planned release |
| **P3** | Minor issue, cosmetic problem | 24 hours | 2+ weeks | Future release |

## Communication Channels Management

### GitHub Discussions
- **Moderation**: Remove off-topic or duplicate discussions
- **Labeling**: Tag by category (bug, feature-request, question, feedback)
- **Pinning**: Pin frequently asked questions
- **Response time**: 24 hours for new threads

### Slack (#skillmeat-beta)
- **Purpose**: Real-time chat, quick questions
- **Response time**: 4 business hours (best effort same-day)
- **Guidelines**: Pin important announcements, use threads for discussions
- **Moderation**: Remove spam, keep on-topic

### Email (beta-support@skillmeat.dev)
- **Response time**: 24 hours
- **Process**: Forward bugs to GitHub, document in Airtable
- **Archive**: All responses stored for audit trail

### Office Hours
- **Schedule**: Thursday 2-3pm PT (fixed, no changes)
- **Attendance**: Optional but encouraged
- **Recording**: Always recorded and available
- **Agenda**: Shared in advance

## Metrics to Track

**Daily metrics:**
- DAU (daily active users)
- Error rate (%)
- P0 bugs (open count)

**Weekly metrics:**
- Completion rate (% participants still active)
- Average satisfaction rating
- New bugs reported
- Feature requests
- Participant retention by day

**End of beta:**
- NPS (Net Promoter Score)
- Overall satisfaction (1-5 scale)
- Documentation clarity rating
- Platform-specific issues
- Blocker bugs (all should be 0)

## Tools and Access

**Required access:**
- `beta-program@skillmeat.dev` email account
- Airtable base (beta participants database)
- Google Forms (feedback collection)
- GitHub repo (issues, discussions)
- Slack #skillmeat-beta and #skillmeat-dev
- Grafana telemetry dashboard
- Loki logs (for debugging)

**Useful commands:**
```bash
# Analyze latest feedback
python scripts/analyze_beta_feedback.py

# Check telemetry for specific participant
curl http://localhost:9090/api/v1/query?query=participant_id%3D%22abc123%22

# Export participants list
airtable export beta-participants.csv
```

## Escalation Chain

**For issues requiring immediate attention:**

1. **On-call Engineer** (P0 bugs)
   - Contact via Slack immediately
   - Provide error logs and reproduction steps

2. **Engineering Manager** (Blocked progress, scope changes)
   - Daily standup discussion
   - Prioritization decisions

3. **Product Manager** (Major feedback themes, roadmap impacts)
   - Weekly planning meeting
   - Strategic decisions

4. **Program Manager** (Participant churn, timeline risks)
   - Immediate discussion
   - Contingency planning

## Weekly Beta Standup Template

**When**: Monday 10am PT

**Attendees**: Program Manager, Engineering Lead, Dev Rel, Product Lead

**Agenda** (30 min total):

1. **Metrics Review** (5 min)
   - DAU, satisfaction, completion rate
   - Any anomalies or concerning trends?

2. **Issue Triage** (10 min)
   - New P0/P1 bugs
   - Unassigned critical issues
   - Resolution status of blockers

3. **Feedback Themes** (5 min)
   - Most common issues reported
   - Most requested features
   - Documentation gaps

4. **This Week's Plan** (5 min)
   - Engineering priorities
   - Who's working on what
   - Expected resolutions

5. **Participant Management** (5 min)
   - Churn rate
   - Engagement status
   - Follow-ups needed

## Documentation Updates

When beta participants identify issues with docs:

1. **Immediately**: Acknowledge the issue
2. **Within 24 hours**: Update docs with clarification
3. **Add note**: "Updated [date] based on beta feedback"
4. **Notify participant**: "Docs updated - thanks again!"

## End-of-Beta Procedures

**Week 6 activities:**

1. **Final Metrics Review**
   - Compare actual metrics against targets
   - Identify any gaps for GA

2. **Bug Triage**
   - All P0/P1 bugs must be fixed
   - Create post-GA backlog for P2/P3

3. **Feature Feedback Summary**
   - Compile most-requested features
   - Make prioritization decisions
   - Communicate plan to participants

4. **Thank You**
   - Send personalized thank you emails
   - Confirm swag/incentives shipping
   - Share release notes credit

5. **Retrospective**
   - Conduct team retrospective
   - What worked well?
   - What to improve for next beta?
   - Lessons learned document

## Participant Thank You Process

**Send after program ends:**

```
Subject: Thank You for Making SkillMeat Better

Dear [name],

Thank you for participating in the SkillMeat closed beta! Your feedback was
invaluable and directly shaped the final product.

**Your Impact:**
- Reported [X] issues, [Y] of which we fixed
- Suggested [Z] features, [A] of which we implemented
- Helped validate [feature] across [platform]

**Rewards**
- [ ] Early access code for v1.0 (expires [date])
- [ ] Swag shipped to [address] (tracking: [number])
- [ ] Special beta contributor badge now active on your profile
- [ ] Your name in v1.0 release notes

**GA Release**
v1.0 launches publicly on [date]. We hope you'll continue using SkillMeat!

Thanks again for believing in us from the beginning.

Best,
SkillMeat Team
```

---

**Questions about beta support?** Post in #skillmeat-internal or contact Program Manager.
