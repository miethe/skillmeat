---
description: Quick MeatyCapture CLI - list/view/search/capture/note/update logs
allowed-tools: [Bash]
---

# MeatyCapture Quick Commands

Default project: skillmeat

## Commands

- List: `meatycapture log list $ARGUMENTS --json`
- View: `meatycapture log view $ARGUMENTS --json`
- Search: `meatycapture log search "$ARGUMENTS" --json`
- Capture: `echo '$ARGUMENTS' | meatycapture log create --json`
- Note: `meatycapture log note add $ARGUMENTS`
- Update: `meatycapture log item update $ARGUMENTS`

## Note Add Usage

```bash
# Add a note to an item
meatycapture log note add <doc-path> <item-id> --content "Note text" [--type TYPE]

# Types: General (default), "Bug Fix Attempt", Validation, Other
meatycapture log note add REQ-20260105-project.md ITEM-01 -c "Fixed by PR #123" -t "Bug Fix Attempt"
```

## Item Update Usage

```bash
# Update item status
meatycapture log item update <doc-path> <item-id> --status done

# Update multiple fields
meatycapture log item update REQ-20260105-project.md ITEM-01 --status in-progress --priority high

# Tag operations
meatycapture log item update doc.md ITEM-01 --tags "tag1,tag2"     # Replace tags
meatycapture log item update doc.md ITEM-01 --add-tags "newtag"   # Add tags
meatycapture log item update doc.md ITEM-01 --remove-tags "oldtag" # Remove tags

# Other fields: --type, --title, --domain, --context
```

Run the appropriate command based on user request.
