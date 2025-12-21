# Participant Invitation Email Template

Use this email template to invite participants to the SkillMeat closed beta program.

---

## Subject Line Options

- "You're invited to test SkillMeat - Closed Beta"
- "Join the SkillMeat Beta (Early Access + Swag)"
- "Test the future of Claude artifact management"
- "Your invitation to shape SkillMeat's future"

---

## Email Body

**To**: [Recipient Name]
**From**: beta-program@skillmeat.dev
**Subject**: You're invited to the SkillMeat closed beta program

---

Hello [Name],

We're building SkillMeat - a personal collection manager for Claude Code artifacts (Skills, Commands, Agents, MCP servers, and Hooks). We're excited to invite you to our closed beta program before our general availability release.

**Why you?**

We hand-picked [X] developers like you to help us test SkillMeat and provide critical feedback. We valued you because:
- You're experienced with [Claude / skill development / team management]
- Your perspective on [specific skill/use case] is invaluable
- We think you'll love using SkillMeat for [specific workflow]

**What's involved?**

- **Time commitment**: 1-2 hours per week for 4-6 weeks
- **Activities**:
  - Install and test SkillMeat features
  - Report bugs you discover
  - Complete a brief satisfaction survey at the end
  - Optional: Join weekly office hours to discuss with the team
- **Platforms**: We need testers on [macOS / Windows / Linux / all three]

**Why participate?**

As a beta participant, you'll receive:

1. **Early Access**: Get v1.0 two weeks before general availability
2. **Beta Contributor Badge**: Special recognition on your marketplace profile
3. **Release Notes Credit**: Your name in the v1.0 release notes
4. **Exclusive Swag**: SkillMeat t-shirt, stickers, and coffee mug
5. **Priority Support**: Direct access to the engineering team during beta
6. **Shape the Product**: Your feedback directly influences features, UX, and docs

**Important: The Problem We're Solving**

Today, managing Claude artifacts across projects is chaotic:
- Skills scattered across multiple GitHub repos
- Version conflicts when team members use different versions
- No centralized place to find quality, tested skills
- No way to bundle and share artifacts with teammates
- Complex setup for integrating MCP servers

SkillMeat solves this with:
- **Collection Management**: Centralized library of all your artifacts
- **Versioning**: Lock versions for consistency, easy updates
- **Team Sharing**: Export bundles, share with teammates
- **Marketplace**: Discover community-contributed artifacts
- **MCP Management**: Deploy and manage MCP servers with simple commands

**Getting Started**

Ready to join? Click the button below to confirm:

[**ACCEPT BETA INVITATION**] (link to signup form)

We'll send you:
1. Installation instructions (5 min)
2. Onboarding guide with first steps (10 min)
3. Slack channel invite for the beta community
4. Link to weekly office hours (Thursdays 2-3pm PT)

**Quick FAQ**

**Q: Will this interfere with my current workflow?**
A: No, SkillMeat installs to a separate directory. You can uninstall anytime.

**Q: Do I need to use the web interface or just CLI?**
A: Your choice! Both are available. We'd love feedback on both.

**Q: What if I find bugs?**
A: Perfect! That's exactly what we want. Report them in GitHub Discussions or Slack.

**Q: Do I have to publish feedback publicly?**
A: No - most feedback is private. We anonymize results in our public retrospective.

**Q: Can I share SkillMeat with my team during beta?**
A: We ask that you don't share beta access outside the official program, but we'd love to invite them! Let us know if you'd like to nominate someone.

**Q: What if I get stuck?**
A: We have weekly office hours (Thursdays 2-3pm PT), Slack channel for quick questions, and email support at beta-support@skillmeat.dev.

**Timeline**

- **Week 1**: Signup, installation, onboarding
- **Week 2-3**: Active testing, issue reporting
- **Week 4**: Feedback collection, surveys
- **Week 5**: Bug fixes and final validation
- **Week 6**: GA release announcement

**The Team**

You'll be working with:
- [Product Manager]: Overall vision and prioritization
- [Engineering Lead]: Building the product, fixing bugs
- [Dev Relations]: Hosting office hours, answering questions
- [Documentation]: Ensuring guides are clear and complete

All of us care deeply about building something useful and trustworthy for the developer community.

**Don't worry - you're in good hands:**
- All SkillMeat code is open source (coming soon)
- Security review completed before beta
- All your data stays on your machine (no cloud storage)
- You control what telemetry is collected (opt-in)

**Next Steps**

1. **Click below** to confirm your participation:
   [**ACCEPT INVITATION**] (link to Google Form)

2. **Tell us a bit about yourself**: We ask a few quick questions about your role and platform.

3. **Watch for our follow-up email**: We'll send installation instructions and Slack invite within 24 hours.

**Questions?**

Reply to this email or ping us in any way that's easiest for you:
- Email: beta-program@skillmeat.dev
- Discussions: github.com/skillmeat/skillmeat/discussions
- Twitter: @skillmeat_dev

We're thrilled to have you on this journey. Your feedback will help us build something that developers love.

See you in the beta!

---

[SkillMeat Team](https://skillmeat.dev)

P.S. - Even if you can't participate right now, we'd love to keep you in the loop. [Join our mailing list](https://skillmeat.dev/subscribe) for GA announcements and product updates.

---

## Signup Form Questions

Link recipients to Google Form with these questions:

**Required Fields:**
- [ ] Full Name
- [ ] Email Address
- [ ] GitHub Username
- [ ] Primary Role
  - [ ] Skill Developer
  - [ ] Team Lead / Manager
  - [ ] Individual User / Solo Developer
  - [ ] Other: ___________
- [ ] Operating System(s) you'll test on
  - [ ] macOS (Intel)
  - [ ] macOS (Apple Silicon)
  - [ ] Linux (Ubuntu)
  - [ ] Linux (Other): ___________
  - [ ] Windows 10
  - [ ] Windows 11
  - [ ] WSL 2
- [ ] Python Version
  - [ ] 3.9
  - [ ] 3.10
  - [ ] 3.11
  - [ ] 3.12
  - [ ] Not sure (we'll help)
- [ ] Time commitment (hours per week)
  - [ ] 1-2 hours (light testing)
  - [ ] 2-4 hours (moderate testing)
  - [ ] 4+ hours (power testing)
- [ ] How you heard about SkillMeat
  - [ ] Direct invitation
  - [ ] GitHub
  - [ ] Twitter
  - [ ] Friend recommendation
  - [ ] Other: ___________

**Optional Fields:**
- [ ] Organization / Company
- [ ] What you hope to use SkillMeat for (textarea)
- [ ] Anything we should know? (textarea)
- [ ] Preferred Slack notification frequency
  - [ ] Daily digest
  - [ ] Every few days
  - [ ] Weekly only
  - [ ] No preference
- [ ] Interested in optional paid/free swag?
  - [ ] Yes, definitely
  - [ ] Maybe
  - [ ] No thanks

---

## Follow-Up Email (Post-Signup)

Send within 24 hours of signup confirmation:

**Subject**: Your SkillMeat Beta Kit is Ready

Hi [Name],

Welcome to the SkillMeat beta! Your signup confirmed. Here's everything you need to get started.

**Installation** (5 minutes)

```bash
# Install from beta release
pip install skillmeat==0.3.0-beta.1

# Verify installation
skillmeat --version
```

[Full installation guide](./beta-onboarding.md)

**Channels**

- **Slack**: Join #skillmeat-beta for real-time chat
- **Discussions**: github.com/skillmeat/skillmeat/discussions
- **Office Hours**: Thursdays 2-3pm PT (optional but recommended!)
- **Email**: beta-support@skillmeat.dev for support

**Your First Steps**

1. Install SkillMeat (see above)
2. Run `skillmeat init` to set up
3. Try adding a skill: `skillmeat add anthropics/skills/document-processor`
4. Explore the web interface: `skillmeat web dev`
5. Join us at Thursday office hours (link in Slack)

**Resources**

- [Onboarding Guide](./beta-onboarding.md) - Full setup walkthrough
- [FAQ](./beta-faq.md) - Common questions
- [Troubleshooting](./beta-onboarding.md#troubleshooting) - Fix issues

**Questions?**

- Quick question? Post in Slack #skillmeat-beta
- Found a bug? Report in GitHub Discussions or Slack
- Need help? Email beta-support@skillmeat.dev

We're excited to have you aboard!

---

[SkillMeat Team](https://skillmeat.dev)

---

## Personalization Tips

To make invitations more compelling:

**For Skill Developers:**
"Your skill development experience makes you perfect for testing our marketplace integration. We'd love your feedback on the skill discovery experience and publication workflow."

**For Team Leads:**
"As someone managing [Claude / AI tool] adoption across your team, we think you'll appreciate SkillMeat's team sharing and artifact management features. Your perspective on collaboration workflows is invaluable."

**For Individual Users:**
"You're building [specific skills/use cases] that align perfectly with SkillMeat's vision. We'd love your feedback on whether the product meets your personal productivity needs."

---

## A/B Testing Subject Lines

Consider testing these subject line variants:

- "You're invited to test SkillMeat - Closed Beta"
- "Join the SkillMeat Beta (Early Access + Swag)"
- "Help shape SkillMeat's future (Closed Beta)"
- "Exclusive invite: Test SkillMeat before anyone else"

Track open rates and signup rates to optimize.

---

## Tracking and Analytics

**Form Setup:**
- Enable form response notifications to beta-program@skillmeat.dev
- Create backup responses in Google Sheets
- Tag responses with signup date and source

**Metrics to track:**
- Email open rate (goal: >40%)
- Invitation acceptance rate (goal: >60%)
- Time from invite to signup (goal: avg <24 hours)
- Platform distribution (goal: 30/30/40 split)
- Role distribution (goal: 40/30/30 split)

---

## Rejection/Not-Yet Email

For developers you want to include in future rounds:

**Subject**: SkillMeat Beta - Come Join Us Soon

Hi [Name],

We loved your interest in the SkillMeat beta! Unfortunately, we've reached capacity for the closed beta round.

**But we don't want to lose you!**

We're planning a second beta round [month/quarter]. Would you be interested in joining then?

In the meantime:
- [Join our mailing list](https://skillmeat.dev/subscribe) for updates
- [Follow on Twitter](https://twitter.com/skillmeat_dev) for announcements
- [Star the repo](https://github.com/skillmeat/skillmeat) on GitHub

GA launches [date], and we'd love to have you as an early user!

Looking forward to connecting down the road.

---

SkillMeat Team
