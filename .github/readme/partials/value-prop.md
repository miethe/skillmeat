### The missing management layer for Claude Code.

**SkillMeat** is a professional-grade collection manager designed to bridge the gap between building Claude Code artifacts and actually using them at scale. It transforms scattered `.claude` files into a version-controlled, searchable, and shareable library.

---

## 💡 Why SkillMeat?

As you build more complex agentic workflows with Claude Code, managing your **Skills, Commands, Agents, and MCP Servers** becomes a bottleneck.

* **The Problem:** Artifacts are often trapped within individual projects. If you improve a "Code Review" skill in one repo, your other ten projects are now running an outdated version. Sharing these tools with a team usually involves brittle copy-pasting.
* **The Solution:** SkillMeat provides a **centralized source of truth**. You manage your artifacts in a global collection and "deploy" them to projects and deployment profiles (`claude_code`, `codex`, `gemini`, `cursor`). When you update the global version, SkillMeat handles the sync, drift detection, and versioning across every project on your machine.

## 🎯 Who is it for?

* **Individual Power Users:** Developers who have a growing library of custom Claude skills and need to keep them in sync across dozens of local repositories.
* **Team Leads & Architects:** Teams looking to standardize their agentic SDLC by sharing "Golden Path" skills, rules, and MCP configurations.
* **Artifact Creators:** Developers building tools for the Claude community who need a structured way to package, sign, and publish their work.

---

## 🚀 Key Capabilities

* **📦 Three-Tier Architecture:** Manage artifacts at the Source (GitHub/Local), Collection (Your Library), and Project (Deployment) levels.
* **🔄 Intelligent Sync:** Bidirectional synchronization with built-in drift detection. See exactly how your project-specific customizations differ from your global library.
* **🛡️ Safety-First Versioning:** Automatic snapshots before any destructive operation. If a new skill version breaks your workflow, roll back with a single command.
* **🌐 Dual Interface:** Use the high-performance **CLI** for your terminal workflows or the **Next.js Web UI** for visual discovery and analytics.
* **🧩 MCP Orchestration:** Centralized management for Model Context Protocol servers—deploy, health-check, and configure environment variables from one place.

---

### Comparison of artifact management with standard Claude Code:

| Feature | Standard Claude Code | With SkillMeat |
| --- | --- | --- |
| **Storage** | Scattered in `.claude/` dirs | Centralized Library (`~/.skillmeat`) |
| **Updates** | Manual copy-paste | Automated Sync & Merge |
| **Versioning** | None | Snapshots & Rollbacks |
| **Sharing** | Manual file transfer | Signed `.skillmeat-pack` Bundles |
| **Visibility** | Terminal only | Full Web Dashboard & Analytics |
