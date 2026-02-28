---
title: Workflow Web UI Guide
description: Complete guide to creating, managing, and running workflows through the SkillMeat web interface
audience:
  - users
tags:
  - workflows
  - web-ui
  - orchestration
  - automation
created: 2026-02-27
updated: 2026-02-27
category: user-guide
status: published
related:
  - docs/user/guides/web-ui-guide.md
---

# Workflow Web UI Guide

This guide covers using the Workflow Builder and Execution Dashboard in the SkillMeat web interface to create, run, and monitor AI agent orchestration workflows.

## Table of Contents

- [Getting Started](#getting-started)
- [Workflow Library](#workflow-library)
- [Creating Workflows](#creating-workflows)
- [Workflow Builder](#workflow-builder)
- [Viewing Workflow Details](#viewing-workflow-details)
- [Running Workflows](#running-workflows)
- [Execution Dashboard](#execution-dashboard)
- [Monitoring Executions](#monitoring-executions)
- [Keyboard Shortcuts](#keyboard-shortcuts)
- [Troubleshooting](#troubleshooting)

## Getting Started

### Accessing Workflows

The Workflows section is available in the main navigation:

1. Click the **Workflows** link in the sidebar
2. You'll see the Workflow Library page with all available workflows
3. The page displays workflows in either **Grid** or **List** view (toggle in the toolbar)

### Empty State

If you haven't created any workflows yet, you'll see an empty state with a **New Workflow** button. Click it to start creating your first workflow.

## Workflow Library

The Workflow Library lets you browse, search, filter, and manage your workflows.

### Viewing Workflows

**Grid View:**
- Visual card layout showing workflows with icons
- Click a card to open workflow details
- Quick action buttons on each card (Run, Edit, Duplicate, Delete)

**List View:**
- Detailed table view with all workflow metadata
- Sortable columns (name, creation date, status)
- Clickable rows to open workflow details

### Switching Views

Use the **View Toggle** buttons in the toolbar to switch between Grid and List views.

### Searching Workflows

1. Click the search field in the toolbar
2. Type keywords to search across:
   - Workflow names
   - Descriptions
   - Tags
   - Authors/creators

3. Results filter in real-time as you type
4. Press **Escape** to clear the search

### Filtering Workflows

**Filter Options:**

- **Status**: All / Draft / Published / Active / Disabled
- **Sort Order**:
  - Name (A-Z)
  - Date Created (newest first)
  - Date Modified (newest first)

Click filter buttons to apply or remove filters. Your selection is shown in the toolbar.

### Clearing Filters

If no workflows match your filters, you'll see an empty state. Click the **Clear filters** button to reset to show all workflows.

### Workflow Card Actions

Hover over any workflow card to see action buttons:

| Action | Purpose |
|--------|---------|
| **Run** | Start a new execution of this workflow |
| **Edit** | Open the workflow in the Builder |
| **Duplicate** | Create a copy of this workflow |
| **Delete** | Remove this workflow (with confirmation) |

## Creating Workflows

### Starting a New Workflow

**Method 1: From the Workflow Library**

1. Click the **New Workflow** button (top right)
2. The Workflow Builder opens with an empty canvas
3. You're ready to add your first stage

**Method 2: From the Workflows Page**

1. Click **New Workflow** on the empty state message
2. The Builder opens immediately

### Workflow Naming

When you create or open a workflow for editing:

1. The workflow name appears in an editable field at the top of the Builder
2. Click the name to edit it inline
3. Type your new name and press Enter to save
4. Changes are saved automatically

Choose clear, descriptive names that indicate the workflow's purpose, like:
- "Code Review Pipeline"
- "Content Generation Workflow"
- "Customer Support Automation"

## Workflow Builder

The Workflow Builder is a drag-and-drop interface for designing workflows without writing code (though code mode is available for advanced users).

### Builder Layout

```
┌─────────────────────────────────────────┐
│ Builder Top Bar (Name, Save, etc.)      │
├────────────────┬──────────────────────┤
│ Left Sidebar   │ Canvas Area           │
│ (Add Stages)   │ (Drag stages here)    │
│                │                       │
│ Stage Editor   │ Stage Cards           │
│ (config)       │ + Connectors          │
└────────────────┴──────────────────────┘
```

**Top Bar:**
- Workflow name (editable)
- Save button
- Status indicator
- Validation messages

**Left Sidebar:**
- **Add Stage** button
- List of existing stages
- Stage Editor panel (appears when you select a stage)

**Canvas:**
- Empty state ("No stages yet") initially
- Drag stages from sidebar to canvas
- Visual connectors show dependencies
- Click stages to edit properties

### Adding Stages

**Method 1: From the Empty Canvas**

1. When the canvas is empty, click the **Add Stage** button in the center
2. A new empty stage appears
3. The Stage Editor panel opens on the right

**Method 2: From the Sidebar**

1. In the left sidebar, click the **+ Add Stage** button
2. A new stage is created
3. The Stage Editor opens for configuration

**Method 3: Duplicate an Existing Stage**

1. Right-click on a stage card or use the stage menu
2. Select **Duplicate**
3. A new stage with the same configuration is created below

### Stage Configuration

When you select a stage, the **Stage Editor** panel appears on the right:

#### Stage Name

- Enter a descriptive name for the stage
- Names should indicate what the stage does
- Example: "Initial Code Analysis", "Generate Response"

#### Stage Type

Select the type of stage:

| Type | Purpose | Notes |
|------|---------|-------|
| **Agent** | Run an AI agent with specific instructions | Standard execution |
| **Gate** | Pause workflow and wait for human approval/rejection | Requires user decision |
| **Parallel** | Run multiple substages simultaneously | All must complete before proceeding |
| **Conditional** | Branch execution based on conditions | Choose path based on rules |

#### Stage Instructions/Configuration

Depending on stage type:

**Agent Stages:**
- Enter the agent name or ID to execute
- Provide system instructions/context
- Configure timeout and retry policies

**Gate Stages:**
- Set approval prompt (what user sees)
- Define approved and rejected paths
- Optionally set auto-timeout

**Parallel Stages:**
- Add multiple substages
- Each runs independently
- Workflow waits for all to complete

**Conditional Stages:**
- Define condition logic
- Map output values to branch paths
- Set default branch if no conditions match

#### Dependencies

Configure which stage(s) must complete before this stage runs:

1. Click the **Dependencies** section
2. Select zero or more predecessor stages
3. The canvas visually shows connecting lines between dependent stages

A stage with no dependencies runs immediately when the workflow starts.

### Stage Organization

#### Reordering Stages

- **Drag stages** on the canvas to reposition them
- **In the sidebar**: Drag stages up/down to reorder execution
- The execution order is determined by dependencies and position

#### Removing Stages

1. Right-click a stage or click the delete icon
2. Confirm deletion
3. The stage is removed and all references are cleaned up

### Visual Feedback

**Stage Cards Show:**

- Stage name (centered, bold)
- Stage type badge (Agent, Gate, Parallel, Conditional)
- Status indicator (unsaved, error, valid)
- Dependency connector lines (arrows pointing to predecessors)
- Action icons (edit, delete, duplicate)

**Color Coding:**

- Green: Valid stage
- Yellow: Unsaved changes
- Red: Configuration error

### Saving the Workflow

#### Automatic Saving

- The Builder auto-saves as you make changes
- A save indicator appears in the top bar
- You'll see "Saving..." briefly, then "Saved"

#### Manual Save

1. Click the **Save** button in the top bar
2. The workflow is persisted to your collection
3. A confirmation appears briefly

#### Validation

Before saving, the Builder checks:

- All stages have names
- Agent stages have agent selection
- Gate stages have approval prompt
- No circular dependencies (A depends on B depends on A)
- No unreachable stages

If validation fails, errors appear above the problematic stage. Fix them before saving.

#### Unsaved Changes Warning

If you navigate away with unsaved changes:

1. A browser confirmation dialog appears
2. Click **Leave** to discard changes or **Stay** to continue editing

### Code Editor Mode

For advanced users, a **Code Editor** mode is available (Haiku/beta):

1. Click the **{ } Code** button in the top bar
2. The YAML representation of your workflow appears
3. Edit the YAML directly:
   - Stage definitions
   - Dependencies
   - Configuration objects

4. Click **Validate** to check syntax
5. Click **Back to Visual** to return to the drag-and-drop builder

**YAML Structure Example:**

```yaml
version: "1.0"
name: "Code Review Pipeline"
stages:
  - id: "initial-analysis"
    name: "Initial Code Analysis"
    type: "agent"
    agent: "code-analyzer"
    config:
      timeout: 300
      instructions: "Analyze the provided code..."

  - id: "approval"
    name: "Review Approval"
    type: "gate"
    config:
      prompt: "Do you approve these changes?"
    dependsOn: ["initial-analysis"]
```

## Viewing Workflow Details

### Opening a Workflow

Click any workflow card or list item to open the **Workflow Details** page:

1. Workflow name and description
2. Stage visualization (graph of stages and dependencies)
3. Metadata:
   - Creation date
   - Last modified date
   - Author
   - Number of stages
   - Number of executions

### Actions on Details Page

| Button | Action |
|--------|--------|
| **Edit** | Open workflow in the Builder for modification |
| **Run** | Start a new execution |
| **Duplicate** | Create a copy of this workflow |
| **Delete** | Remove workflow (with confirmation) |

### Stage Visualization

The stage visualization shows:

- **Nodes**: Each stage as a colored box
- **Labels**: Stage names inside nodes
- **Type Badges**: Icon indicating stage type (agent, gate, etc.)
- **Connectors**: Arrows showing stage dependencies
- **Direction**: Left to right; top to bottom for complex flows

Click a stage node to:
- Highlight it
- See detailed configuration
- View any validation messages

## Running Workflows

### Starting a Workflow Execution

**Method 1: From Workflow Card**

1. In the Workflow Library, click the **Run** button on a workflow card
2. The **Run Workflow** dialog opens
3. Fill in parameters (see below)
4. Click **Start Execution**

**Method 2: From Workflow Details**

1. Open a workflow
2. Click the **Run** button in the header
3. The **Run Workflow** dialog opens

**Method 3: From Workflow Editor**

1. While editing, click the **Run** button in the top bar
2. Current workflow is executed with your parameters

### Run Workflow Dialog

The dialog has two sections:

#### Parameters Section

Dynamic parameter fields appear based on the workflow's parameter schema:

**Parameter Types:**

| Type | Input | Examples |
|------|-------|----------|
| **String** | Text field | Repository name, code snippet |
| **Number** | Number input | Timeout in seconds, max results |
| **Boolean** | Toggle switch | Enable/disable options |
| **Select** | Dropdown | Choose from predefined options |
| **Textarea** | Multi-line text | Long content, code blocks |

**Field Validation:**

- **Required fields**: Must have a value (marked with asterisk *)
- **Default values**: Pre-filled automatically
- **Inline help text**: Describes what the parameter does
- **Error messages**: Show if required field is empty

**Filling Parameters:**

1. Each parameter shows its name and description
2. Type or select values in the input fields
3. Default values are pre-filled; override them if needed
4. Required fields must be filled before you can run

#### Advanced Section (Optional)

Click **Advanced Settings** to expand:

- **Context Module Override**: Select a custom context module (if configured)
- **Project Override**: Run in a different project context
- **Environment Variables**: Set temporary env vars for this execution

### Starting the Execution

1. Fill all required parameters
2. Click the **Start Execution** button
3. The workflow execution begins
4. You're automatically redirected to the **Execution Dashboard**

## Execution Dashboard

The Execution Dashboard provides real-time monitoring of a running workflow.

### Dashboard Layout

```
┌─────────────────────────────────────────┐
│ Execution Header                        │ (sticky)
│ (Workflow name, run ID, status, actions)│
├─────────────────────────────────────────┤
│ Progress Bar                            │
│ (Stage progress, connection status)     │
├───────────────────┬─────────────────────┤
│ Stage Timeline    │ Execution Detail    │
│ (left column)     │ (right side)        │
│ ┌───────────────┐ │ ┌─────────────────┐ │
│ │ Stage 1       │ │ │ Stage info      │ │
│ │ ✓ completed  │ │ │ Agent details   │ │
│ ├───────────────┤ │ │ Timing info     │ │
│ │ Stage 2       │ │ │ Context used    │ │
│ │ → running     │ │ │ Inputs/Outputs  │ │
│ ├───────────────┤ │ │ Error (if fail) │ │
│ │ Stage 3       │ │ │ Approval (gate) │ │
│ │ ◯ pending     │ │ └─────────────────┘ │
│ └───────────────┘ └─────────────────────┘
│                 │ Log Viewer            │
│                 │ (shows logs)          │
└─────────────────┴─────────────────────────┘
```

### Execution Header

**Top Sticky Bar** showing:

- **Workflow Name** (clickable link to workflow details)
- **Run ID** (truncated, full ID on hover)
- **Status Badge** (color-coded for status)
- **Started Timestamp** (when execution began)
- **Action Buttons**:
  - **Pause** (if running)
  - **Resume** (if paused)
  - **Cancel** (stop execution)
  - **Re-run** (start execution again)

On narrow screens, action buttons collapse into a **...** menu.

### Progress Bar

Below the header, a compact progress bar shows:

- **Stage Progress**: Visual indicator of how many stages have completed
- **Percentage**: (2/5 stages complete)
- **Connection Status**:
  - Green dot: Connected to execution stream
  - Yellow dot: Reconnecting
  - Gray dot: Disconnected (results still load from API)

### Stage Timeline

**Left Column** lists all stages in execution order:

#### Stage Card Components

Each stage shows:

- **Stage Name** (bold, clickable)
- **Status Icon**:
  - ✓ (checkmark): Completed successfully
  - ⏸ (pause): Paused (awaiting approval or user action)
  - → (arrow): Currently running
  - ◯ (circle): Pending (waiting for dependencies)
  - ✕ (X): Failed with error
- **Stage Type Badge** (Agent, Gate, Parallel, etc.)
- **Duration** (how long it took, or "in progress" for running)
- **Time Started** (relative time: "5m ago")

#### Clicking a Stage

1. Click any stage card in the timeline
2. The **Execution Detail** panel on the right updates immediately
3. Logs below update to show that stage's output
4. The selected stage is visually highlighted

#### Stage Status Meanings

| Status | Meaning | What's happening |
|--------|---------|------------------|
| ◯ Pending | Not started yet | Waiting for prerequisites |
| → Running | Currently executing | Agent is processing |
| ⏸ Paused | Awaiting input | Gate stage, needs approval |
| ✓ Completed | Finished successfully | Results are available |
| ✕ Failed | Encountered an error | Error details shown below |
| ↻ Retrying | Attempting again | Failed, automatic retry active |

### Execution Detail Panel

**Right Column** shows full details for the selected stage:

#### Stage Header

- Stage name
- Type badge (Agent, Gate, etc.)
- Status badge (color-coded)
- Relative time started

#### Agent Information

(Only for Agent stages)

- **Agent Name**: Name of the AI agent that ran
- **Agent Type**: Category (research, coding, analysis, etc.)
- **Tools Available**: List of tools the agent can access
  - Each tool shows icon and name
  - Hover for description

#### Timing Section

A grid showing:

| Field | Meaning |
|-------|---------|
| **Started** | Absolute timestamp when stage began |
| **Duration** | How long stage took to complete, or live counter if running |
| **Ended** | Absolute timestamp when stage finished (or "—" if still running) |

Live updates: Running stages show a live counter ("2m 30s elapsed...").

#### Context Consumed

Shows how much context (tokens) the stage used:

- **Input Tokens**: Tokens sent to the agent
- **Output Tokens**: Tokens generated by the agent
- **Total**: Sum of input + output
- **Model**: Which model was used

#### Inputs / Outputs Sections

**Collapsible sections** showing stage data:

**Inputs:**
- Parameters passed to this stage
- Output from previous stage(s)
- Formatted as collapsible JSON tree (expand/collapse)

**Outputs:**
- Results returned by this stage
- Formatted as collapsible JSON tree
- Click to expand and view full content
- Copy button to copy to clipboard

#### Error Callout

(Only if stage failed)

Shows in a red alert box:

- **Error Title**: "Stage Failed"
- **Error Message**: Detailed reason (API error, timeout, agent error, etc.)
- **Stack Trace** (if available): Technical details
- **Recovery Suggestion**: How to fix (if applicable)

#### Gate Approval Panel

(Only for Gate stages awaiting approval)

Shows:

- **Approval Prompt**: The question/message to approve
- **Context Preview**: Summary of what led to this gate
- **Two Buttons**:
  - **Approve** (green): Proceed to next stage
  - **Reject** (red): Fail this stage, terminate workflow

**Loading state** on buttons while request is in flight. Confirmation appears after submission.

### Log Viewer

**Below Execution Detail**, shows real-time logs for the selected stage:

#### Log Features

- **Live Scrolling**: New logs appear at the bottom automatically
- **Auto-scroll**: Scrolls to bottom as new logs arrive
- **Search**: Search field to filter logs by keyword
- **Log Level Filter**:
  - All / Error / Warning / Info / Debug
  - Only show logs matching selected level

#### Log Entries

Each log line shows:

- **Timestamp**: When the log was generated (relative or absolute)
- **Level Badge**: ERROR (red), WARN (yellow), INFO (blue), DEBUG (gray)
- **Message**: The actual log text
- **Context** (if available): Additional metadata

#### Log Behavior

- **Persistence**: Logs are stored; you can view them even after execution completes
- **Streaming**: During active execution, logs appear in real-time via Server-Sent Events (SSE)
- **Fallback**: If connection drops, logs are loaded from the API on-demand
- **Persistence**: Scroll up to view earlier logs

## Monitoring Executions

### All Executions Page

View all workflow executions across the entire collection:

1. Click **All Executions** in the Workflows section
2. A table appears showing all runs, newest first

#### Execution Columns

| Column | Content |
|--------|---------|
| **Run ID** | Truncated execution ID; hover for full ID |
| **Workflow** | Workflow name (clickable link) |
| **Status** | Color-coded badge (Running, Completed, Failed, etc.) |
| **Started** | Relative time (e.g., "5m ago") |
| **Duration** | How long execution took (or "in progress") |
| **Trigger** | How it was started (Manual, API, Schedule) |

#### Filtering Executions

1. **Status Filter**: Dropdown to show only executions with a specific status
2. **Sort Order**: Click the "Started" column header or use the sort button to toggle ascending/descending
3. Click **Clear filters** to reset

#### Clicking an Execution

Click any row to navigate to the **Execution Dashboard** for that run.

### Workflow-Specific Executions

View all executions for a single workflow:

1. Open a workflow
2. Click the **Executions** tab or "View all runs" link
3. Shows only runs for that workflow
4. Same filtering and sorting as All Executions

### Execution Status Reference

| Status | Color | Meaning |
|--------|-------|---------|
| **Running** | Blue | Stages are currently executing |
| **Pending** | Slate | Execution queued, not yet started |
| **Completed** | Green | All stages finished successfully |
| **Failed** | Red | One or more stages failed |
| **Paused** | Amber | Execution paused (gate awaiting approval) |
| **Cancelled** | Zinc | User cancelled the execution |
| **Waiting for Approval** | Violet | Gate stage is awaiting human decision |

## Keyboard Shortcuts

**Workflow Library:**

- `/` - Focus search field
- `Esc` - Clear search
- `g w` - Go to Workflows page
- `g e` - Go to All Executions

**Workflow Builder:**

- `Ctrl+S` - Save workflow
- `Esc` - Close without saving
- `Ctrl+Z` - Undo (if available)
- `Ctrl+Y` - Redo (if available)

**Execution Dashboard:**

- `Space` - Toggle pause/resume
- `x` - Cancel execution
- `r` - Re-run workflow
- `?` - Show help

**General:**

- `?` - Show available shortcuts
- `Ctrl+K` - Quick command palette

## Troubleshooting

### Workflows Won't Load

**Problem:** Workflow Library shows error or blank

**Solutions:**

1. Refresh the page: `Ctrl+R` or `Cmd+R`
2. Hard refresh (clear cache): `Ctrl+Shift+R` or `Cmd+Shift+R`
3. Check browser console for errors: Press `F12`, check Console tab
4. Verify API is running: Check that the backend server is accessible
5. Restart web server:
   ```bash
   skillmeat web stop && skillmeat web start
   ```

### Workflow Won't Save

**Problem:** Save button greyed out or shows "Error saving"

**Solutions:**

1. Check for validation errors (red message above stages)
2. Fix any configuration issues (missing stage names, etc.)
3. Try clearing browser cache: `Ctrl+Shift+Delete` (Ctrl+Shift+Del on Windows)
4. Ensure you have write permissions to the collection
5. Check backend logs for details:
   ```bash
   tail -f ~/.skillmeat/logs/api.log
   ```

### Execution Won't Start

**Problem:** Run dialog appears but "Start Execution" button does nothing

**Solutions:**

1. Check that all required parameters (marked with *) are filled
2. Look for inline error messages under parameter fields
3. Close dialog and try again
4. Check that the workflow has been saved successfully
5. Verify backend is accessible (check connection indicator)

### Logs Not Updating (Disconnected)

**Problem:** Connection indicator shows disconnected, logs aren't updating

**Solutions:**

1. **Check Connection**: Ensure network is connected
2. **Page Refresh**: Reload the dashboard page
3. **Browser Console**: Check for network errors (F12)
4. **Firewall/Proxy**: Verify SSE (Server-Sent Events) isn't blocked
5. **Backend Status**: Restart backend:
   ```bash
   skillmeat web stop && skillmeat web start
   ```

Logs will continue to load from API even if SSE connection drops, just without live updates.

### Stage Won't Complete

**Problem:** Stage stuck in "Running" state indefinitely

**Solutions:**

1. **Check Logs**: Look for error messages in the log viewer
2. **Timeout**: If timeout is configured, execution may be waiting for it
3. **Cancel Execution**: Click the **Cancel** button if stuck
4. **Check Agent**: Verify the agent is configured correctly and accessible
5. **Review Input**: Check that inputs passed to the stage are valid

### Gate Approval Not Working

**Problem:** Approve/Reject buttons don't respond

**Solutions:**

1. Ensure execution is still running (not already completed)
2. Verify this stage is actually a Gate stage
3. Try clicking the button again
4. Refresh page and retry
5. Check browser console for JavaScript errors

### Memory/Performance Issues

**Problem:** Dashboard is slow or uses lots of memory

**Solutions:**

1. **Close Other Tabs**: Reduces browser memory usage
2. **Collapse Sections**: Close expanded Inputs/Outputs sections
3. **Disable Debug Logs**: If viewing very verbose logs, toggle log level filter
4. **Smaller Workflows**: Test with simpler workflows first
5. **Browser Restart**: Restart browser to clear memory

### Getting Help

If issues persist:

1. **Collect Information:**
   - Screenshot or description of the issue
   - Steps to reproduce
   - Browser type and version
   - Any error messages from console (F12)

2. **Check Logs:**
   ```bash
   # Frontend errors
   tail -f ~/.skillmeat/logs/web.log

   # Backend errors
   tail -f ~/.skillmeat/logs/api.log
   ```

3. **Enable Debug Mode:**
   ```bash
   skillmeat web start --api-log debug
   ```

4. **Contact Support:**
   - GitHub Issues: https://github.com/skillmeat/skillmeat/issues
   - Discussions: https://github.com/skillmeat/skillmeat/discussions

## See Also

- [Web UI Guide](./web-ui-guide.md) - General web interface overview
- [Collections Management](./web-ui-guide.md#collections-browser) - Managing your artifact library
- [Analytics Guide](./using-analytics.md) - Understanding usage patterns
