# Session Recovery Skill Specification

**Status**: Draft
**Version**: 0.1.0
**Date**: 2025-12-23
**Author**: AI-Generated Spec (Post-Crash Analysis)
**Context**: Created after recovering from multi-agent parallel execution crash

---

## Executive Summary

This spec defines a Claude Code skill for recovering from crashed, failed, or interrupted sessions. The skill enables rapid state reconstruction by analyzing agent logs, verifying on-disk changes, and creating resumption plans for interrupted work.

### Problem Statement

**Current State**:
- Claude Code sessions can crash during multi-agent parallel execution
- Agent conversation logs exist but are buried in `~/.claude/projects/` directories
- No standardized workflow for determining what was completed vs interrupted
- Recovery is ad-hoc, requiring manual log parsing and verification
- Knowledge of recovery techniques is not documented

**Desired State**:
- Standardized skill invoked immediately after session recovery
- Automated discovery and analysis of interrupted agent logs
- Clear status report: COMPLETE, IN_PROGRESS, FAILED, UNKNOWN for each task
- Generated resumption plan with ready-to-execute Task() commands
- Prevention recommendations to avoid future crashes

---

## Core Functionality

### 1. Agent Log Discovery

**Log Location Pattern**:
```
~/.claude/projects/{project-path-with-dashes}/
├── agent-{8-char-id}.jsonl    # Subagent conversation logs
├── agent-{8-char-id}.jsonl
└── ...
```

**Discovery Techniques**:

| Technique | Command | Use Case |
|-----------|---------|----------|
| By recency | `find {log_dir} -name "agent-*.jsonl" -mmin -{minutes}` | Find recently active agents |
| By ID pattern | `ls {log_dir} \| grep -E "(id1\|id2\|id3)"` | Match known agent IDs |
| By size | `find {log_dir} -name "*.jsonl" -size +10k -mtime -1` | Find substantial logs |
| All recent | `ls -lt {log_dir}/agent-*.jsonl \| head -20` | List recent by modification time |

**Path Derivation**:
```javascript
// Project path: /Users/name/dev/project
// Log directory: ~/.claude/projects/-Users-name-dev-project/
const logDir = '~/.claude/projects/' + projectPath.replace(/\//g, '-').replace(/^-/, '');
```

### 2. Log Analysis

**JSONL Format**:
Each line is a JSON object representing a conversation turn with structure:
```json
{
  "message": {
    "role": "assistant",
    "content": [
      {"type": "tool_use", "name": "Write", "input": {"file_path": "..."}},
      {"type": "text", "text": "..."}
    ]
  }
}
```

**Extraction Patterns**:

| Data Point | Extraction Command | Purpose |
|------------|-------------------|---------|
| Files created | `grep -o '"file_path":"[^"]*"' log.jsonl \| sort -u` | Verify deliverables |
| Test results | `grep -E 'passed\|failed\|PASSED\|FAILED' log.jsonl` | Check test status |
| Final status | `tail -5 log.jsonl \| jq -r '.message.content[]'` | Completion assessment |
| Tool count | `grep -c '"type":"tool_use"' log.jsonl` | Progress indication |
| Error messages | `grep -i 'error\|failed\|exception' log.jsonl` | Identify failures |

**Status Determination Logic**:
```
IF log contains "COMPLETE" or "successfully" in final messages → COMPLETE
ELIF log contains uncaught errors in final 10 lines → FAILED
ELIF log size > threshold AND recent modification → IN_PROGRESS (likely crashed)
ELIF log is small with no file writes → NOT_STARTED
ELSE → UNKNOWN (requires manual review)
```

### 3. On-Disk Verification

Cross-reference agent deliverables against actual filesystem:

```bash
# For each file_path extracted from logs:
if [ -f "$file_path" ]; then
    echo "VERIFIED: $file_path exists"
    # Check modification time against session
    stat -f "%Sm" "$file_path"
else
    echo "MISSING: $file_path not found"
fi
```

**Verification Checklist**:
- [ ] All expected files exist
- [ ] Files have content (not empty)
- [ ] Modification time aligns with session
- [ ] Tests pass (if test files created)
- [ ] No syntax errors (quick lint check)

### 4. Recovery Report Generation

**Report Structure**:
```markdown
# Session Recovery Report
Generated: {timestamp}
Project: {project_path}

## Agent Status Summary

| Agent ID | Task | Status | Files Created | Tests |
|----------|------|--------|---------------|-------|
| a91845a | P2-T1: MatchAnalyzer | COMPLETE | 2 | 33/33 ✓ |
| abec615 | P2-T2: SemanticScorer | COMPLETE | 4 | 17/17 ✓ |
| xyz1234 | P4-T3: RatingDialog | IN_PROGRESS | 1 | - |

## Completed Work
- MatchAnalyzer with 97.67% coverage
- SemanticScorer with embedding provider abstraction
...

## Interrupted Tasks
### P4-T3: RatingDialog
- Last known state: Component scaffolding created
- Missing: Tests, accessibility, documentation
- Resumption command:
  ```
  Task("ui-engineer-enhanced", "Complete P4-T3: RatingDialog component...")
  ```

## Recommended Actions
1. Commit completed work (files: {...})
2. Resume interrupted tasks with provided commands
3. Update progress tracking
```

---

## Skill Architecture

### File Structure

```
.claude/skills/recovering-sessions/
├── SKILL.md                           # Main skill definition
├── techniques/
│   ├── discovering-agent-logs.md      # Log location and discovery
│   ├── parsing-jsonl-logs.md          # JSONL extraction patterns
│   ├── verifying-on-disk-state.md     # Filesystem verification
│   └── generating-resumption-plans.md # Recovery report format
├── scripts/
│   ├── find-recent-agents.js          # Node.js log discovery
│   ├── analyze-agent-log.js           # Single log analysis
│   └── generate-recovery-report.js    # Full report generation
├── templates/
│   └── recovery-report.md             # Report template
└── references/
    └── prevention-patterns.md         # Crash prevention guidance
```

### SKILL.md Content

```yaml
---
name: recovering-sessions
description: |
  Recover from crashed, failed, or interrupted Claude Code sessions. Use this skill when:
  - Claude Code session crashed during multi-agent parallel execution
  - User reports their previous session was interrupted
  - Need to determine what work was completed vs incomplete
  - Want to generate resumption commands for interrupted tasks
  - Recovering from context window exhaustion
  Analyzes agent logs, verifies on-disk state, and creates resumption plans.
---
```

### Core Workflow

```
1. GATHER CONTEXT
   - Read implementation plan/PRD for expected deliverables
   - Run `git status` to see uncommitted changes
   - Get project log directory path

2. DISCOVER AGENT LOGS
   - Find recent agent logs (by time, ID, or size)
   - Correlate with known task assignments

3. ANALYZE EACH LOG (parallel haiku subagents)
   For each log file:
   - Extract files created/modified
   - Find test results
   - Determine completion status
   - Note any errors

4. VERIFY ON-DISK STATE
   - Check each expected file exists
   - Run test suites for created tests
   - Validate code quality (lint)

5. GENERATE RECOVERY REPORT
   - Summarize completed vs incomplete work
   - Create resumption Task() commands
   - Recommend commit strategy

6. EXECUTE RECOVERY
   - Commit completed work
   - Update progress tracking
   - Resume interrupted tasks (with user approval)
```

---

## Agent Delegation Strategy

**Token Efficiency**: Use haiku subagents for log analysis (cheap, parallelizable).

```javascript
// Launch parallel log analyzers
const analyses = await Promise.all(
  agentLogs.map(log =>
    Task("codebase-explorer", {
      model: "haiku",
      prompt: `Analyze agent log at ${log.path}:
        1. Did it complete successfully?
        2. What files did it create/modify?
        3. What test results (if any)?
        4. Any errors or issues?
        Return: TASK_ID, STATUS, FILES, TESTS, NOTES`
    })
  )
);
```

**Background Execution Pattern**:
```javascript
// For large batches, use background execution
const tasks = logs.map(log =>
  Task("codebase-explorer", {
    model: "haiku",
    run_in_background: true,
    prompt: `Analyze ${log.path}...`
  })
);

// Collect results
const results = await Promise.all(
  tasks.map(t => TaskOutput(t.id, { block: true }))
);
```

---

## Prevention Recommendations

### 1. Update execute-phase Command

**Current Issue**: Launching many parallel subagents without checkpointing.

**Recommended Changes**:

```markdown
## execute-phase Improvements

### Batch Size Limits
- Max 3-4 parallel tasks per batch (not 6+)
- Use run_in_background with periodic status checks
- Add progress heartbeat every 5 minutes

### Checkpointing
- After each task completion, immediately update progress file
- Write checkpoint before launching next batch
- Include resumption state in checkpoint

### Example Enhanced Workflow
1. Read progress file YAML
2. Launch batch_1 tasks (max 3)
3. Wait for completion OR 10-minute timeout
4. Update progress immediately for completed tasks
5. Launch batch_2 only after batch_1 complete
6. Repeat with explicit checkpoints between batches
```

### 2. CLAUDE.md Updates

Add recovery guidance to CLAUDE.md:

```markdown
## Session Recovery

If session crashes during parallel execution:
1. Invoke `/recovering-sessions` skill
2. Review generated recovery report
3. Commit completed work
4. Resume interrupted tasks

### Prevention Practices
- Keep parallel batches small (3-4 agents max)
- Use background execution with timeout monitoring
- Update progress tracking after each task completion
- Prefer sequential execution for critical paths
```

### 3. Artifact Tracking Improvements

**Enhanced YAML Frontmatter**:
```yaml
# In progress files, add:
session_tracking:
  last_checkpoint: "2025-12-23T10:30:00Z"
  active_agents: ["a91845a", "abec615"]
  batch_in_progress: 2

# After each task:
tasks:
  - id: "TASK-1.1"
    status: "complete"
    completed_at: "2025-12-23T10:35:00Z"
    agent_id: "a91845a"  # For log correlation
```

### 4. Agent Execution Patterns

**Recommended Pattern** (fault-tolerant):
```javascript
// Instead of launching all at once:
const allTasks = [...]; // Many tasks

// Execute in smaller batches with checkpointing:
const BATCH_SIZE = 3;
for (let i = 0; i < allTasks.length; i += BATCH_SIZE) {
  const batch = allTasks.slice(i, i + BATCH_SIZE);

  // Launch batch
  const results = await Promise.all(
    batch.map(t => executeTask(t))
  );

  // Checkpoint immediately
  await updateProgressFile(results);

  // Brief pause between batches
  await sleep(1000);
}
```

### 5. Heartbeat Pattern

Add periodic status updates during long operations:

```javascript
// In long-running tasks, emit heartbeats
const heartbeat = setInterval(() => {
  appendToProgressFile({
    timestamp: new Date().toISOString(),
    status: 'active',
    current_operation: describeCurrentWork()
  });
}, 5 * 60 * 1000); // Every 5 minutes

try {
  // ... do work ...
} finally {
  clearInterval(heartbeat);
}
```

---

## Implementation Phases

### Phase 1: Core Skill (MVP)

- [ ] SKILL.md with discovery and analysis workflows
- [ ] Log discovery techniques documentation
- [ ] JSONL parsing patterns
- [ ] Basic recovery report template
- [ ] Manual verification checklist

### Phase 2: Automation Scripts

- [ ] `find-recent-agents.js` - Discover agent logs
- [ ] `analyze-agent-log.js` - Parse single log
- [ ] `generate-recovery-report.js` - Create full report
- [ ] Integration with artifact-tracking skill

### Phase 3: Prevention Integration

- [ ] Update execute-phase command with batching
- [ ] Add checkpointing to progress files
- [ ] Implement heartbeat pattern
- [ ] CLAUDE.md recovery guidance

### Phase 4: Advanced Features

- [ ] Auto-detection of crash scenarios
- [ ] Intelligent task resumption
- [ ] Session health monitoring
- [ ] Integration with observability/telemetry

---

## Usage Examples

### Example 1: Post-Crash Recovery

```
User: "Claude crashed while I had multiple agents running. Help me recover."

Skill Workflow:
1. Identify project log directory
2. Find recent agent logs (last 3 hours)
3. Analyze each log in parallel (haiku subagents)
4. Cross-reference with git status
5. Generate recovery report
6. Offer to commit completed work
7. Provide resumption commands for incomplete tasks
```

### Example 2: Session Handoff

```
User: "I need to hand off this session to continue later."

Skill Workflow:
1. Identify active/recent work
2. Capture current git state
3. Document in-progress tasks
4. Update progress tracking with session notes
5. Generate handoff summary with resumption instructions
```

### Example 3: Proactive Health Check

```
User: "Check if any of my recent agent work was incomplete."

Skill Workflow:
1. Scan recent agent logs (last 24 hours)
2. Identify any without clear completion markers
3. Check if corresponding files exist
4. Report any gaps or incomplete work
5. Suggest remediation if needed
```

---

## Scripts Specification

### find-recent-agents.js

```javascript
#!/usr/bin/env node
/**
 * Discover agent logs from recent sessions
 * Usage: node find-recent-agents.js [--minutes N] [--project PATH]
 */
import { readdir, stat } from 'fs/promises';
import { homedir } from 'os';
import { join } from 'path';

const DEFAULT_MINUTES = 180; // 3 hours

async function findRecentAgents(projectPath, minutes = DEFAULT_MINUTES) {
  const logDir = join(
    homedir(),
    '.claude/projects',
    projectPath.replace(/\//g, '-').replace(/^-/, '')
  );

  const cutoff = Date.now() - (minutes * 60 * 1000);
  const files = await readdir(logDir);

  const agentLogs = [];
  for (const file of files) {
    if (!file.startsWith('agent-') || !file.endsWith('.jsonl')) continue;

    const filePath = join(logDir, file);
    const stats = await stat(filePath);

    if (stats.mtimeMs > cutoff) {
      agentLogs.push({
        id: file.match(/agent-([a-f0-9]+)\.jsonl/)?.[1],
        path: filePath,
        modified: new Date(stats.mtimeMs),
        size: stats.size
      });
    }
  }

  return agentLogs.sort((a, b) => b.modified - a.modified);
}
```

### analyze-agent-log.js

```javascript
#!/usr/bin/env node
/**
 * Analyze a single agent log for recovery
 * Usage: node analyze-agent-log.js <log-path>
 */
import { readFile } from 'fs/promises';

async function analyzeLog(logPath) {
  const content = await readFile(logPath, 'utf-8');
  const lines = content.trim().split('\n');

  const result = {
    totalMessages: lines.length,
    filesCreated: new Set(),
    filesModified: new Set(),
    testResults: null,
    status: 'UNKNOWN',
    errors: [],
    lastActivity: null
  };

  for (const line of lines) {
    try {
      const entry = JSON.parse(line);
      const content = entry.message?.content || [];

      for (const block of content) {
        if (block.type === 'tool_use') {
          // Extract file operations
          if (block.name === 'Write' && block.input?.file_path) {
            result.filesCreated.add(block.input.file_path);
          }
          if (block.name === 'Edit' && block.input?.file_path) {
            result.filesModified.add(block.input.file_path);
          }
        }
        if (block.type === 'text') {
          // Look for test results
          const testMatch = block.text.match(/(\d+)\s+(passed|tests?\s+passed)/i);
          if (testMatch) {
            result.testResults = testMatch[0];
          }
          // Look for completion markers
          if (/complete|success|finished/i.test(block.text)) {
            result.status = 'COMPLETE';
          }
          // Look for errors
          if (/error|failed|exception/i.test(block.text)) {
            result.errors.push(block.text.slice(0, 200));
          }
        }
      }
    } catch (e) {
      // Skip malformed lines
    }
  }

  // Convert Sets to Arrays for JSON output
  result.filesCreated = [...result.filesCreated];
  result.filesModified = [...result.filesModified];

  // Determine status if not already set
  if (result.status === 'UNKNOWN') {
    if (result.errors.length > 0) result.status = 'FAILED';
    else if (result.filesCreated.length > 0) result.status = 'IN_PROGRESS';
  }

  return result;
}
```

---

## Success Metrics

| Metric | Target |
|--------|--------|
| Time to recovery report | < 2 minutes |
| Accuracy of status detection | > 90% |
| Files correctly identified | > 95% |
| User satisfaction with resumption | > 85% |
| Crash prevention (with recommendations) | 50% reduction |

---

## Open Questions

1. **Auto-recovery**: Should the skill auto-invoke after detected crashes?
   - Pro: Faster recovery
   - Con: May interfere with user intent
   - **Recommendation**: Suggest but don't auto-invoke

2. **Log retention**: How long to keep agent logs for recovery?
   - Current: Unclear retention policy
   - **Recommendation**: 7-day default, configurable

3. **Partial work**: How to handle tasks that are 50% complete?
   - Option A: Start from scratch
   - Option B: Attempt to continue
   - **Recommendation**: Assess completion, offer both options

4. **Cross-session recovery**: Can we recover work from days-old sessions?
   - Depends on log retention
   - git history helps
   - **Recommendation**: Support with degraded confidence

---

## Appendix: Real-World Recovery Example

**Scenario**: Session crashed with 6 parallel agents running (from 2025-12-23 incident)

**Recovery Steps Taken**:
1. User provided known agent IDs: a91845a, abec615, adad508
2. Found logs using: `find ~/.claude/projects/... -name "*.jsonl" -mtime -1`
3. Launched 6 parallel haiku subagents to analyze logs
4. Verified files on disk with `git status`
5. Ran `pytest` to confirm 98 tests passing
6. Created progress tracking document
7. Committed 34 files with comprehensive message

**Outcome**: Full recovery achieved, all completed work preserved, clear next steps identified.

**Lessons Learned**:
- Smaller parallel batches prevent crashes
- Progress tracking should be updated after each task
- Agent IDs should be captured in progress files
- Haiku subagents are ideal for log analysis (cheap, fast)

---

## References

- Agent log format: Claude Code internal documentation
- JSONL specification: https://jsonlines.org/
- Artifact tracking skill: `.claude/skills/artifact-tracking/`
- Execute-phase command: `.claude/commands/execute-phase.md`
