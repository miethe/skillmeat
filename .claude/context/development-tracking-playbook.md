# Development Tracking Playbook

Task-specific guidance for MeatyCapture request-log workflows.

## Structure

- Bugs: append to daily bug log (`Bug Log - YYYY-MM-DD`).
- Enhancements/features/ideas/questions/tasks: one doc per request unless tightly related.

## Fast Path

Use `mc-quick.sh` for short captures:

```bash
mc-quick.sh TYPE DOMAIN SUBDOMAIN "Title" "Problem" "Goal" [notes...]
```

Types: `enhancement`, `bug`, `idea`, `task`, `question`.

## JSON Path

Use JSON payloads when notes need escaping/newlines, or when appending to an existing document with richer fields.

## When To Load

Load this file only when the task includes request logging, bug tracking, or `/mc` workflows.
