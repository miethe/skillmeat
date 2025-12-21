# Project Scaffolding Walkthrough - Video Script

**Duration**: 4:50 (under 5 minutes)
**Target Audience**: New users, developers
**Learning Outcome**: How to scaffold a complete Claude Code project in under 2 minutes using SkillMeat templates
**Recording Format**: Screen capture with voiceover

---

## Scene 1: Introduction (30 seconds)

**[VISUAL: Title card with animated text]**

**VOICEOVER:**
"Tired of manually setting up Claude Code projects? Watch how to scaffold a complete project structure in under two minutes using SkillMeat templates—no copy-pasting, no manual file creation."

**[VISUAL: Fade to browser showing SkillMeat web UI]**

**VOICEOVER:**
"In this walkthrough, you'll see how to go from zero to a fully-configured FastAPI and Next.js project with CLAUDE.md, specs, rules, and context files all ready to use."

**[VISUAL: Show project structure tree briefly in background]**

**VOICEOVER:**
"Let's dive in."

**[Timing note: 0:00-0:30]**

---

## Scene 2: Browse Templates (45 seconds)

**[VISUAL: Show browser at SkillMeat web UI home page]**

**VOICEOVER:**
"Start by navigating to the Templates page. Here you'll find pre-built project templates for different tech stacks."

**[VISUAL: Click on Templates menu → page loads with template grid]**

**VOICEOVER:**
"SkillMeat provides templates for common combinations. You can see FastAPI + Next.js Full-Stack, Python CLI tools, and more."

**[VISUAL: Slowly pan across three template cards:
1. FastAPI + Next.js Full-Stack
2. Python CLI with Tooling
3. Node.js TypeScript Backend]**

**VOICEOVER:**
"For this example, we're using the FastAPI and Next.js full-stack template—perfect for building modern web applications with Python backend and React frontend."

**[VISUAL: Hover over FastAPI + Next.js template to show highlight]**

**VOICEOVER:**
"Click on the template to see what's included."

**[VISUAL: Click template → modal opens showing template details]**

**VOICEOVER:**
"The template includes everything you need: CLAUDE.md with your project configuration, documentation policies, rules for your backend API layer, rules for your frontend hooks, and context files for your development team."

**[VISUAL: Show template detail modal with entity list:
- CLAUDE.md (main configuration and delegation patterns)
- doc-policy-spec.md (documentation standards)
- routers.md (API router patterns)
- hooks.md (React hooks patterns)
- backend-api-patterns.md (API design context)]**

**[Timing note: 0:30-1:15]**

---

## Scene 3: Configure Project (60 seconds)

**[VISUAL: Scroll to bottom of modal, show Deploy button]**

**VOICEOVER:**
"When you're ready, click Deploy Template to start the configuration wizard."

**[VISUAL: Click "Deploy Template" button → configuration form appears]**

**VOICEOVER:**
"First, give your project a name. This will be used throughout your CLAUDE.md and project configuration."

**[VISUAL: Focus on project name input field]**

**[TYPING ANIMATION: Type "Task Manager API"]**

**VOICEOVER:**
"Let's call this one Task Manager API."

**[VISUAL: Move to next field—project path]**

**VOICEOVER:**
"Next, specify where on your machine this project will live."

**[VISUAL: Click on project path field]**

**[TYPING ANIMATION: Type ~/projects/task-manager]**

**VOICEOVER:**
"We're placing it in our projects directory."

**[VISUAL: Move to description field]**

**VOICEOVER:**
"Add a brief description. This will be embedded in your CLAUDE.md to help your team understand the project at a glance."

**[VISUAL: Click on description field]**

**[TYPING ANIMATION: Type "FastAPI + Next.js task management application with real-time updates and team collaboration features"]**

**VOICEOVER:**
"And finally, your name as the author. This gets recorded in your project configuration."

**[VISUAL: Click on author field]**

**[TYPING ANIMATION: Type "Your Name"]**

**VOICEOVER:**
"Now here's the powerful part—watch as the template variables are automatically substituted throughout all the files. Your project name, description, and author go everywhere they're needed."

**[VISUAL: Zoom on preview panel showing CLAUDE.md snippet with:
- Project name "Task Manager API" highlighted
- Description substituted
- Author name in frontmatter
- Each instance highlighted with subtle pulse animation]**

**VOICEOVER:**
"No manual find-and-replace. No copy-pasting. All automatic."

**[Timing note: 1:15-2:15]**

---

## Scene 4: Deploy (45 seconds)

**[VISUAL: Scroll to deploy button, form is fully filled]**

**VOICEOVER:**
"Once you've filled in the configuration, click Deploy to create your project."

**[VISUAL: Click "Deploy" button → progress indicator appears]**

**[VISUAL: Show progress bar animating]**

**VOICEOVER:**
"The deployment process takes just a few seconds. It's creating all five entities from the template."

**[VISUAL: Progress updates:
- "Creating CLAUDE.md... ✓"
- "Creating doc-policy-spec.md... ✓"
- "Creating routers.md... ✓"
- "Creating hooks.md... ✓"
- "Creating backend-api-patterns.md... ✓"]**

**VOICEOVER:**
"And just like that, your project is deployed."

**[VISUAL: Deployment completes, success screen appears (< 5 seconds duration)]**

**VOICEOVER:**
"The success screen shows you a preview of the file tree that was created. All your project files are ready to go."

**[VISUAL: Show file tree preview in success modal:
.claude/
├── CLAUDE.md
├── specs/
│   └── doc-policy-spec.md
├── rules/
│   ├── api/
│   │   └── routers.md
│   └── web/
│       └── hooks.md
└── context/
    └── backend-api-patterns.md]**

**[Timing note: 2:15-3:00]**

---

## Scene 5: Verify Project Structure (60 seconds)

**[VISUAL: Close success modal → show file explorer opening]**

**VOICEOVER:**
"Let's verify the project was created correctly by opening it in the file explorer."

**[VISUAL: File explorer opens, navigate to ~/projects/task-manager]**

**VOICEOVER:**
"Here's our project directory. Notice the .claude folder—this contains all your project configuration and agent context."

**[VISUAL: Expand .claude folder to show complete directory structure]**

**VOICEOVER:**
"Let's dive into each section. The CLAUDE.md file is your project's configuration hub."

**[VISUAL: Open .claude/CLAUDE.md in text editor]**

**VOICEOVER:**
"When we open it, you can see that all your project variables have been automatically substituted."

**[VISUAL: Scroll through CLAUDE.md, highlight these sections with yellow boxes:
- Project name: "Task Manager API" in description
- Project description: substituted in overview
- Author name: in header/attribution
- References to project-specific paths]**

**VOICEOVER:**
"Your project name appears in the description. Your description is woven throughout the configuration. Your author name is recorded. And every path reference is correctly configured."

**[VISUAL: Collapse CLAUDE.md, expand specs/ folder]**

**VOICEOVER:**
"The specs folder contains your documentation policy. This file defines what should and shouldn't be documented in your project—keeping documentation focused and maintainable."

**[VISUAL: Show doc-policy-spec.md in preview]**

**VOICEOVER:**
"Next, the rules folder. This is where agent-specific patterns live."

**[VISUAL: Expand rules/ → show api/ and web/ subfolders]**

**VOICEOVER:**
"For your backend, you've got routers.md with FastAPI patterns. For your frontend, hooks.md with React patterns."

**[VISUAL: Open routers.md briefly to show contents]**

**VOICEOVER:**
"And finally, the context folder. This contains architectural guides and pattern documentation that your AI agents will reference."

**[VISUAL: Expand context/ folder → show backend-api-patterns.md]**

**VOICEOVER:**
"Everything is organized, labeled, and ready for your team to use immediately."

**[Timing note: 3:00-4:00]**

---

## Scene 6: Conclusion & Call to Action (30 seconds)

**[VISUAL: Zoom out to show full project structure on screen]**

**VOICEOVER:**
"Let's recap what we just accomplished. In under two minutes, we scaffolded a complete project with:"

**[VISUAL: Bullet points appear on screen one by one:
- ✓ Fully configured CLAUDE.md with delegation patterns
- ✓ Documentation standards and policies
- ✓ Backend API layer patterns (routers, schemas)
- ✓ Frontend patterns (hooks, components)
- ✓ Architectural context for your AI agents]**

**VOICEOVER:**
"No manual file creation. No copy-pasting. No struggling with folder structure. Everything is ready for you to open in Claude Code and start building."

**[VISUAL: Show Claude Code opening the project]**

**VOICEOVER:**
"The benefits? Your project is consistent from day one. Your agents have the context they need to work effectively. Your team follows the same patterns. And you save hours of setup time."

**[VISUAL: Fade to SkillMeat website]**

**VOICEOVER:**
"Try this yourself right now at skillmeat.dev. Choose a template, configure it in 60 seconds, and start building."

**[VISUAL: Show call-to-action button: "Get Started" with skillmeat.dev URL]**

**VOICEOVER:**
"Your next Claude Code project is just two minutes away."

**[VISUAL: Fade to black with text: "SkillMeat - Scaffold. Code. Ship. Faster."]**

**[Timing note: 4:00-4:50]**

---

## Technical Notes for Editor

### Recording Settings
- **Resolution**: 1920x1080 (or higher for 4K)
- **Frame Rate**: 30fps
- **Audio Sample Rate**: 48kHz
- **Bitrate**: 6 Mbps H.264

### Keyboard & Mouse
- Use smooth mouse movements (enable cursor highlighting)
- Type at natural speed, not too fast
- Use keyboard shortcuts where appropriate (Cmd+C, Ctrl+V)

### Timing Cues
- Total video: 4:50
- Scene 1 (Intro): 0:00-0:30
- Scene 2 (Browse): 0:30-1:15 (add 15s buffer)
- Scene 3 (Configure): 1:15-2:15 (full 60s)
- Scene 4 (Deploy): 2:15-3:00 (45s, keep deployment quick)
- Scene 5 (Verify): 3:00-4:00 (tight 60s)
- Scene 6 (Conclusion): 4:00-4:50 (50s)

### Visual Elements to Prepare
- **Title Card**: "Project Scaffolding with SkillMeat"
- **Subtitle Cards**: For each scene transition
- **Highlights/Boxes**: Yellow or blue highlight boxes around key UI elements
- **Cursor Trail**: Enable to make click targets obvious
- **Zoom Effects**: Use 1.2x-1.5x zoom on text to ensure readability
- **Progress Indicators**: Animated checkmarks for file creation

### Audio Production
- **Music**: Light background instrumental (low volume, fadeout at end)
- **Voiceover**: Clear, friendly tone—not rushed. Allow natural pauses between sentences
- **Sound Effects**: Subtle "whoosh" for transitions, "ding" for completion
- **Final Audio Mix**: Voiceover at -10dB, music at -20dB, SFX at -15dB

### Post-Production Checklist
- [ ] Color correct all scenes (slight boost to saturation for UI elements)
- [ ] Add captions/subtitles (SRT format)
- [ ] Sync audio with video (voiceover should match on-screen actions)
- [ ] Add transition effects between scenes (cross dissolve, 0.5s duration)
- [ ] Include project setup timestamps in video description
- [ ] Add linked chapters for easy navigation:
  - 0:00 - Introduction
  - 0:30 - Browse Templates
  - 1:15 - Configure Project
  - 2:15 - Deploy
  - 3:00 - Verify Structure
  - 4:00 - Conclusion

### Accessibility
- Ensure all text on screen is large enough (18pt minimum)
- Provide captions for all dialogue (required by WCAG 2.1 AA)
- Describe visual elements that are crucial to understanding
- Use sufficient color contrast for any highlighted elements

---

## Script Delivery Tips

### Voice Tone
- **Friendly & Conversational**: Imagine explaining to a colleague over coffee
- **Confident but Not Rushed**: You know this works; let that come through
- **Emphasize Saves**: Highlight time and effort savings at key moments
- **Pause Before Key Points**: "And here's the powerful part..." [pause 1s]

### Pacing
- Speak at natural pace (150-160 words per minute)
- Pause 1-2 seconds at scene transitions
- Allow on-screen animations to complete before speaking next line
- Never talk over complex visual changes

### Emphasis Words
- Bold these when recording voiceover:
  - "**under two minutes**"
  - "**no copy-pasting**"
  - "**automatically**"
  - "**ready to go**"

---

## File Structure Reference

The deployed project creates this exact structure:

```
~/.claude/
├── CLAUDE.md                           # Main project config (personalized)
├── specs/
│   └── doc-policy-spec.md             # Documentation standards
├── rules/
│   ├── api/
│   │   └── routers.md                 # FastAPI patterns
│   └── web/
│       └── hooks.md                   # React patterns
└── context/
    └── backend-api-patterns.md        # API design guide
```

Each file is personalized with:
- **Project Name**: "Task Manager API"
- **Description**: From user input
- **Author**: From user input
- **Paths**: Correctly configured for project location

---

## Related Documentation

- **Web UI Guide**: `/docs/user/guides/web-ui-guide.md`
- **Templates Overview**: (link to templates documentation)
- **CLAUDE.md Reference**: `/CLAUDE.md`
- **Project Setup**: `/docs/user/quickstart.md`

---

## Metadata

**Script Version**: 1.0
**Last Updated**: 2025-12-15
**Status**: Ready for Production
**Approval**: Pending
