---
title: SkillMeat Onboarding Script
description: 30-minute facilitated onboarding script for new SkillMeat users with group walkthrough
audience: trainers, facilitators, team leads
tags:
  - training
  - onboarding
  - script
  - facilitation
created: 2025-11-17
updated: 2025-11-17
category: Training
status: Published
related:
  - README.md
  - ./trainer-guide.md
---

# SkillMeat Onboarding Script

**Estimated Duration**: 30 minutes
**Audience**: New SkillMeat users (individuals or small groups)
**Prerequisites**: SkillMeat installed (`skillmeat --version` works)
**Setup**: Participants on same or similar network

## Pre-Training Checklist (5 minutes before)

- [ ] Test your own SkillMeat installation
- [ ] Have sample artifact specs ready (e.g., `anthropics/skills/code-review`)
- [ ] Verify web interface works: `skillmeat web dev`
- [ ] Gather participant emails for follow-up
- [ ] Have written materials available (links or printouts)

## Session Structure

**Total Time**: ~40 minutes (30 min + 10 min Q&A)

1. Introduction (5 min)
2. First Collection Walkthrough (10 min)
3. Web Interface Demo (10 min)
4. Marketplace Overview (5 min)
5. Wrap-up and Resources (5 min)

---

## Part 1: Introduction (5 minutes)

### What to Say

> "Welcome to SkillMeat! I'm [Your Name], and today I'm going to show you how to get up and running with SkillMeat in about 30 minutes.
>
> By the end of this session, you'll be able to:
> - Create your first collection
> - Add artifacts from GitHub
> - Deploy them to your Claude projects
> - Browse the marketplace
> - Use the web interface
>
> Whether you're working solo or with a team, SkillMeat helps you manage all your Claude artifacts - skills, commands, agents - in one place.
>
> Let's start by making sure everyone has SkillMeat installed. Can everyone run this command in your terminal?"

### Verification Step

**Command for participants to run**:
```bash
skillmeat --version
```

**What they should see**:
```
skillmeat, version 0.3.0-beta
```

**If it fails**:
- "If you don't see the version, SkillMeat might not be installed. After this session, see the [quick start guide](../guides/quickstart.md) for installation help."
- "We'll come back to installation questions at the end."

### Set Expectations

> "We'll go hands-on, so feel free to follow along on your machine as we go. If you get stuck, just raise your hand and I'll help. Let's start!"

---

## Part 2: First Collection Walkthrough (10 minutes)

### Introduction

> "First, we're going to create your first collection. A collection is like a library of all your Claude artifacts - think of it as your personal repository where you keep everything organized."

### Step 1: Initialize Collection (3 minutes)

**Show command**:
```bash
skillmeat init
```

**What to explain**:
> "This command initializes a new collection. It creates a configuration file at `~/.skillmeat/collection.toml` that stores information about all your artifacts.
>
> Let me show you what happens..."

**Run it** and show output:
```
Initialized collection at ~/.skillmeat/
Created collection.toml with default settings
```

**Have participants try**:
> "Now you try - go ahead and run `skillmeat init` on your machine. You might get a message that it already exists, which is fine."

**Wait for confirmations**, then:
> "Great! Everyone should see either 'Initialized' or 'Already exists'. Either way, you're good to go."

### Step 2: Add First Artifact (4 minutes)

**Explain what we're doing**:
> "Now we're going to add an artifact. Artifacts are the building blocks - they could be skills that add capabilities, commands that provide utilities, or agents that automate tasks.
>
> Let me add a skill from GitHub. This skill is a code review assistant that analyzes code and provides feedback."

**Show command**:
```bash
skillmeat add anthropics/skills/code-review
```

**Explain the format**:
> "The format is `username/repo/path[@version]`. You can also add skills from local paths with `./path/to/skill`."

**Run it** and show output:
```
Added skill: code-review
Source: anthropics/skills/code-review
Version: latest
Scope: user
Status: Ready to deploy
```

**Have participants try**:
> "Pick an artifact you're interested in. Want another code-related one? Try:
> ```bash
> skillmeat add anthropics/skills/code-review
> ```
> Or search for something in the marketplace with:
> ```bash
> skillmeat marketplace-search productivity
> ```
> Then add something that interests you."

**Wait for participants to add**, then:
> "Excellent! You've just added your first artifact. Each artifact is versioned, so you can track updates and safely manage changes."

### Step 3: List Artifacts (2 minutes)

**Show command**:
```bash
skillmeat list
```

**Example output**:
```
Collection: default
├── code-review (skill)
│   Source: anthropics/skills/code-review
│   Version: latest
│   Status: Ready
└── [any other artifacts added]
```

**Explain**:
> "This shows you everything in your collection. The status tells you if each artifact is ready to deploy. Notice the version - it's tracking 'latest', which means when the upstream artifact updates, you can update with a simple command.
>
> You can also see full details with `skillmeat show <name>`."

---

## Part 3: Web Interface Demo (10 minutes)

### Introduction

> "Now let me show you the web interface. This is the beautiful dashboard where you can see all your artifacts, deploy them, and monitor everything happening."

### Start Web Server (2 minutes)

**Show command**:
```bash
skillmeat web dev
```

**Explain while it starts**:
> "This starts a local web server. It should automatically open in your browser at `http://localhost:3000`."

**Wait for it to load**, then:
> "You should see the dashboard now. If not, try opening `http://localhost:3000` manually in your browser."

### Demo: Collections Dashboard (3 minutes)

**Show the dashboard**:
> "You're looking at the collections dashboard. This is your command center. On the left you can see all your collections and artifacts. On the right is a quick view showing statistics about your collection.

**Walk through**:
1. **Collections list** - "Click on an artifact to see its details"
2. **Artifact card** - Click on one and show the detail drawer
3. **Metadata panel** - "Here's all the information about this artifact"
4. **Deploy button** - "See that deploy button? We'll talk about that in a second"

### Demo: Deploy Interface (3 minutes)

**Show deployment UI**:
> "Let me click the deploy button to show you how easy deployment is."

**Click Deploy**:
> "You would select which Claude Code project to deploy this to, confirm, and it's deployed. You'll see real-time progress with a progress bar and status updates.

> After deployment, the artifact is available in your Claude projects - no copying files or manual installation needed."

**Explain features**:
- "Real-time progress with Server-Sent Events"
- "Shows what was deployed and when"
- "You can deploy multiple artifacts at once"
- "Easy rollback if you need to undo"

### Demo: Analytics (2 minutes)

**If time permits**, scroll to analytics section:
> "SkillMeat also tracks how you're using your artifacts. This helps you understand which artifacts are most useful, and when to clean up ones you're not using anymore.

> The analytics are private - SkillMeat only tracks usage on your machine. No data leaves your computer."

---

## Part 4: Marketplace Overview (5 minutes)

### Introduction

> "One of the cool features is the marketplace. You can browse artifacts created by others, install what's useful, and even publish your own."

### Search the Marketplace

**Show command**:
```bash
skillmeat marketplace-search productivity
```

**Explain**:
> "This searches the public marketplace for artifacts related to 'productivity'. You'll see results with names, descriptions, and ratings from other users."

**Show installing**:
```bash
skillmeat marketplace-install skillmeat-42
```

> "Installing is super easy - one command. The artifact is downloaded, verified, and added to your collection."

### Marketplace in Web UI

**Switch to web UI**:
> "You can also browse the marketplace right here in the web interface. It's easier to explore visually than with command line - you can filter by category, see ratings and reviews, and install with one click."

### Publishing Your Own

> "Once you create your own artifacts, you can publish them to the marketplace so others can use them. We have a guide on publishing if you're interested."

**Point to resource**:
- "See the docs at [publishing guide](../guides/publishing-to-marketplace.md) for complete details"

---

## Part 5: Wrap-Up and Resources (5 minutes)

### Key Takeaways

> "Let me recap what you've learned today:
>
> 1. **Create a collection** - `skillmeat init`
> 2. **Add artifacts** - `skillmeat add <spec>`
> 3. **See everything** - `skillmeat list`
> 4. **Use the web interface** - `skillmeat web dev`
> 5. **Deploy to Claude** - Click deploy in web UI
> 6. **Browse marketplace** - `skillmeat marketplace-search`
>
> These are the core workflows. Everything else builds on these basics."

### Resources for Learning More

> "Here are the key resources for diving deeper:
>
> **Quick References**:
> - [CLI Commands Reference](./cli-cheat-sheet.md) - Quick lookup for all commands
> - [Web UI Shortcuts](./web-ui-shortcuts.md) - Keyboard shortcuts and tips
>
> **Detailed Guides**:
> - [Web UI Guide](../guides/web-ui-guide.md) - Full walkthrough of web interface
> - [Team Sharing Guide](../guides/team-sharing-guide.md) - Share with teammates
> - [Marketplace Guide](../guides/marketplace-usage-guide.md) - Publish and share
>
> **Getting Help**:
> - Documentation: https://docs.skillmeat.dev
> - GitHub Discussions: https://github.com/miethe/skillmeat/discussions
> - Email: support@skillmeat.dev"

### Next Steps

> "Here's what I recommend you do next:
>
> 1. **Explore** - Add a few more artifacts that look interesting
> 2. **Experiment** - Try deploying one to a project
> 3. **Learn** - Read the guides that match your needs
> 4. **Share** - If you're on a team, check out the team sharing guide
>
> And don't hesitate to reach out with questions!"

### Collect Feedback

> "Before we wrap up, could you answer a quick question? Take 30 seconds to fill out this feedback form: [Training Feedback Form](https://forms.skillmeat.dev/training-feedback)
>
> Your feedback helps us improve training for everyone else."

---

## Part 6: Q&A and Troubleshooting (10 minutes)

### Q&A Format

> "Now let's open it up for questions. What would you like to know?"

### Common Questions and Answers

#### Q: What's the difference between skills, commands, and agents?

> "Great question!
>
> **Skills** add new capabilities to Claude - like code review, documentation, design.
>
> **Commands** are utilities and tools - things like API clients, file formatters, testing frameworks.
>
> **Agents** can autonomously perform tasks - like running workflows, automating processes, or making decisions.
>
> All three are managed the same way in SkillMeat - you add them, deploy them, and track them."

#### Q: Where do the artifacts go when I deploy them?

> "They go to your Claude Code projects. SkillMeat handles the deployment automatically. They're stored in the `.claude/skills/` directory in your project."

#### Q: Can I use SkillMeat if I'm working solo?

> "Absolutely! SkillMeat is designed for individuals and teams alike. Solo users benefit from version tracking, easy updates, and search. Teams benefit from that plus sharing and collaboration."

#### Q: What if I want to modify an artifact?

> "You can! There are different update strategies:
> - Overwrite: Replace with upstream version
> - Merge: Keep your changes and merge new updates
> - Fork: Create your own variant
>
> See the [updating guide](../guides/updating-safely.md) for details."

#### Q: How do I know when artifacts have updates available?

> "Run `skillmeat status` to check. You can update with `skillmeat update <name>` when you're ready."

### Installation Issues

If someone didn't get SkillMeat installed:

> "I see you're having installation trouble. Here's what to do:
>
> 1. Make sure you have Python 3.9+ installed: `python --version`
> 2. Install with: `pip install skillmeat`
> 3. Verify: `skillmeat --version`
>
> The [quick start guide](../guides/quickstart.md) has detailed step-by-step instructions for your OS.
>
> Feel free to reach out to us after this for help: support@skillmeat.dev"

### Web Interface Not Starting

> "If the web interface won't start:
>
> 1. Make sure Node.js 18+ is installed: `node --version`
> 2. Try a different port: `skillmeat web dev --port 3001`
> 3. Check if port 3000 is in use: `lsof -i :3000`
>
> If you're still stuck, we have a [troubleshooting guide](../guides/troubleshooting.md)."

---

## Follow-Up Email Template

**Send this after the training:**

---

**Subject**: SkillMeat Onboarding - Next Steps & Resources

Hi [Participants],

Thanks for joining today's SkillMeat onboarding! Here are the resources we discussed plus some next steps.

**Quick References**:
- CLI Commands: [./cli-cheat-sheet.md](./cli-cheat-sheet.md)
- Web UI Shortcuts: [./web-ui-shortcuts.md](./web-ui-shortcuts.md)
- Common Workflows: [./common-workflows.md](./common-workflows.md)

**Detailed Guides** (read these for deeper learning):
- Web UI Guide: https://github.com/miethe/skillmeat/docs/guides/web-ui-guide.md
- Team Sharing Guide: https://github.com/miethe/skillmeat/docs/guides/team-sharing-guide.md
- Marketplace Guide: https://github.com/miethe/skillmeat/docs/guides/marketplace-usage-guide.md
- MCP Management: https://github.com/miethe/skillmeat/docs/guides/mcp-management.md

**Recommended Next Steps**:
1. Add 2-3 artifacts that interest you
2. Deploy one to a test project
3. Explore the web interface more
4. Read one detailed guide that matches your needs

**Support**:
- Full Documentation: https://docs.skillmeat.dev
- GitHub Discussions: https://github.com/miethe/skillmeat/discussions
- Email: support@skillmeat.dev
- Office Hours: Thursdays 2-3pm PT

**Your Feedback**: Please take 1 minute to complete our [training feedback form](https://forms.skillmeat.dev/training-feedback). Your input helps us improve!

Questions? Reply to this email or ask in GitHub Discussions.

Best,
SkillMeat Team

---

## Facilitation Tips

### Keep It Interactive

- Have participants try commands as you demonstrate
- Encourage questions throughout
- Ask "what do you see?" to check understanding
- Pair experienced users with newcomers

### Adjust Pace

- If group is struggling: Slow down, skip web demo, focus on CLI
- If group is advanced: Expand on MCP and marketplace
- Have "stretch topics" ready for fast movers

### Handle Distractions

- "Great question, let me note that and we'll cover it in the resources section"
- Keep time sacred - don't let Q&A run over
- Schedule office hours for extended discussions

### Engagement Strategies

- Start with hands-on (not just demo)
- Show a real use case they care about
- Use humor and relatable examples
- Celebrate wins ("Nice, you added your first artifact!")

### Recovery Techniques

- **If demo breaks**: "Let me show you the command line - it's faster anyway"
- **If someone is stuck**: Have a buddy help while you continue
- **If lost focus**: "Let's recap - here's what we've done so far..."

---

## Success Metrics

After this 30-minute session, participants should be able to:

- [ ] Run `skillmeat --version` (verification)
- [ ] Initialize a collection: `skillmeat init`
- [ ] Add an artifact: `skillmeat add <spec>`
- [ ] List artifacts: `skillmeat list`
- [ ] Start web UI: `skillmeat web dev`
- [ ] Navigate web dashboard
- [ ] Understand artifact types
- [ ] Know where to find help

---

## Variations by Audience

### For Teams
- Emphasize team sharing section
- Show vault setup examples
- Discuss governance and policies
- Highlight merge/conflict resolution

### For Developers
- Expand marketplace publishing section
- Show artifact structure
- Discuss versioning strategies
- Cover security best practices

### For Admins
- Skip marketplace, focus on MCP
- Show observability overview
- Discuss deployment at scale
- Cover troubleshooting tools

---

**Version**: 1.0
**Last Updated**: November 17, 2025
**Questions?** See [Trainer Guide](./trainer-guide.md)
