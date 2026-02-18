# Agent Teams Patterns

When to use Agent Teams vs standard Task() subagents for parallel work.

## Decision Framework

| Criterion | Subagents (Task) | Agent Teams |
|-----------|------------------|-------------|
| Scope | Single task, 1-3 files | Multi-component feature, 5+ files |
| Duration | Minutes | Session-long |
| Context | Shares parent context window | Each gets full 200K context |
| Communication | Returns result to parent only | Peer-to-peer messaging |
| Parallelism | Limited by parent context | True independent parallel |
| Cost | Cheaper per task | More expensive (N full sessions) |
| Coordination | Parent orchestrates all | Task list + direct messaging |

## Team Templates

### Feature Team (API + Frontend + Tests)

```python
# 1. Create team
TeamCreate(team_name="feature-team", description="Implement [feature name]")

# 2. Create tasks
TaskCreate(subject="Implement API endpoint", description="...")
TaskCreate(subject="Build frontend component", description="...")
TaskCreate(subject="Validate implementation", description="...")

# 3. Spawn teammates
Task("python-backend-engineer", "Join team and work on API tasks",
     team_name="feature-team", name="backend-dev")
Task("ui-engineer-enhanced", "Join team and work on frontend tasks",
     team_name="feature-team", name="frontend-dev")
Task("task-completion-validator", "Join team and validate completed work",
     team_name="feature-team", name="validator")

# 4. Assign tasks via TaskUpdate
# 5. Monitor via TaskList
# 6. Shutdown via SendMessage(type="shutdown_request")
# 7. Cleanup via TeamDelete
```

### Debug Team (Parallel Investigation)

```python
TeamCreate(team_name="debug-team", description="Investigate [issue]")

Task("codebase-explorer", "Search for patterns related to the bug",
     team_name="debug-team", name="explorer", model="haiku")
Task("python-backend-engineer", "Implement fix once root cause is found",
     team_name="debug-team", name="fixer")
```

### Refactor Team (Cross-Layer Changes)

```python
TeamCreate(team_name="refactor-team", description="Refactor [system]")

Task("python-backend-engineer", "Handle backend changes",
     team_name="refactor-team", name="backend-dev")
Task("ui-engineer-enhanced", "Handle frontend changes",
     team_name="refactor-team", name="frontend-dev")
Task("code-reviewer", "Review all changes continuously",
     team_name="refactor-team", name="reviewer")
```

## Team Lifecycle

1. **Create**: `TeamCreate(team_name=..., description=...)`
2. **Plan**: Create tasks with `TaskCreate`, set dependencies with `TaskUpdate`
3. **Spawn**: Launch teammates with `Task(agent_type, prompt, team_name=..., name=...)`
4. **Assign**: Use `TaskUpdate(taskId, owner="teammate-name")` to assign work
5. **Monitor**: Use `TaskList` to check progress, respond to teammate messages
6. **Shutdown**: `SendMessage(type="shutdown_request", recipient="teammate-name")`
7. **Cleanup**: `TeamDelete()` after all teammates have shut down

## When NOT to Use Teams

- Quick features touching < 3 files (use parallel Task() calls instead)
- Exploration-only work (use codebase-explorer directly)
- Documentation generation (single agent handles fine)
- Code review (single agent handles fine)
- Batch operations on similar files (parallel Task() is simpler)

Teams add coordination overhead. Only use when the context window benefit outweighs the cost.
