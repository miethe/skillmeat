# Updating Item Status

How to update the status of captured request-log items. Direct file editing is required until a CLI update command exists.

---

## Workflow

1. **Find the item** - Search or list to locate the item
2. **View the document** - Confirm item details and current status
3. **Edit the markdown** - Update the `**Status:**` field directly

---

## Find the Item

```bash
# Search by keyword
meatycapture log search "validation" PROJECT_NAME --json

# Search by item ID
meatycapture log search "REQ-20251229-project-01" PROJECT_NAME --json

# List documents then view
meatycapture log list PROJECT_NAME --json
```

Get the document path from search results:

```bash
DOC_PATH=$(meatycapture log search "validation" PROJECT_NAME --json | jq -r '.matches[0].doc_path')
```

---

## View Current Status

```bash
# View full document
meatycapture log view "$DOC_PATH" --json

# Get specific item
meatycapture log view "$DOC_PATH" --json | jq '.items[] | select(.id == "REQ-20251229-project-01")'
```

---

## Status Values

| Status | Description |
|--------|-------------|
| `triage` | New item, needs review and prioritization |
| `backlog` | Reviewed, accepted, not yet scheduled |
| `planned` | Scheduled for upcoming work |
| `in-progress` | Currently being worked on |
| `done` | Completed |
| `wontfix` | Closed without action (duplicate, invalid, deferred) |

---

## Typical Transitions

```
triage -> backlog -> planned -> in-progress -> done
                 \-> wontfix (at any stage)
```

- **triage -> backlog**: After review, confirmed valid
- **backlog -> planned**: Scheduled for a sprint/milestone
- **planned -> in-progress**: Work started
- **in-progress -> done**: Work completed
- **any -> wontfix**: Closed without implementation

---

## Edit Status in Markdown

The status field appears in the item header:

```markdown
**Type:** bug | **Domain:** core | **Priority:** medium | **Status:** triage
```

### Before

```markdown
### REQ-20251229-project-01 - Sanitize user input

**Type:** bug | **Domain:** core | **Priority:** critical | **Status:** triage
**Tags:** security, input-validation

- Problem: Project names not sanitized.
- Goal: Add validation regex.
```

### After

```markdown
### REQ-20251229-project-01 - Sanitize user input

**Type:** bug | **Domain:** core | **Priority:** critical | **Status:** done
**Tags:** security, input-validation

- Problem: Project names not sanitized.
- Goal: Add validation regex.
```

---

## Batch Status Updates

For multiple items, use pattern matching with your editor or sed:

```bash
# Update all triage items to backlog in a document
sed -i '' 's/\*\*Status:\*\* triage/**Status:** backlog/g' "$DOC_PATH"
```

**Caution**: Review changes before committing. Batch updates may affect unintended items.

---

## Verification

After editing, verify the change:

```bash
meatycapture log view "$DOC_PATH" --json | jq '.items[] | {id: .id, status: .status}'
```

---

## Notes

- Direct file editing required until CLI `update` command is implemented
- Status changes do not auto-update document `updated_at` metadata (CLI append does)
- Consider adding a note when closing as `wontfix` explaining the reason
