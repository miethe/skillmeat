# Enhancements - Agent and Context Entities

**Date:** December 14, 2025

## Context

Most modern Agentic AI systems utilitize key context files, ie CLAUDE.md or AGENTS.md, to define the roles, responsibilities, and capabilities of various agents within the system. Additionally, systems like Claude Code allow progressive disclosure, rules files, etc.

I want to enhance our app to support these concepts as additional entities, along with skills, agents, etc. This will allow SkillMeat to manage the full lifecycle of Claude deployments and manage structured specs and policies.

Consider what this enhancement would look like. How it might best be implemented, how to design the entities, etc.

We should be adding a new type to Collections for said files, perhaps with sub-types for the various kinds (CLAUDE.md-type files, context specs (ie what we have in `.claude/specs`), rules ie `.claude/rules`, etc).

We should also consider how we could create Project deployments directly in SkillMeat, from there deploying to a codebase/repo. Currently, the flow is to setup a project and then link it to SkillMeat, then managing the artifacts from there. This would go a step further and enable managing the full lifecycle of the project from SkillMeat, including the agent specs, context files, rules, etc.

Also consider the best way to integrate this natively into both the web app and CLI, so users can easily create, manage, and deploy their projects.