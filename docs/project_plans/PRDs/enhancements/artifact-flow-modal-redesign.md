---
status: inferred_complete
---
# Artifact Flow Modal Redesign

This document outlines the design specifications for the redesigned Artifact Flow Modal in the Skillmeat web application. The goal of this redesign is to provide a consistent, intuitive, and efficient user interface for managing artifact synchronization across Source, Collection, and Project levels from a single location.

## Overall Structure

### 1. Modal Container and Header

* **Container:** A standard modal window overlaid on the application background with a semi-transparent backdrop.
* **Header Title:** Dynamic title in the format "Artifact Synchronization: [Artifact Name] ([Artifact Type])". (e.g., "python-skill (Skill)").
* **Close Action:** A standard 'X' icon in the top right to dismiss the modal.
* **Navigation Tabs:** Below the title, a horizontal tab bar containing four items: "Overview", "Sync Status", "Version History", and "Settings". The "Sync Status" tab is currently active (underlined or highlighted).

### 2. Main Layout Structure

The main content area under the tabs is divided vertically into a top flow visualization banner, and below that, a three-panel layout:

* **Left Panel (Sidebar):** Fixed width, for file navigation.
* **Middle Panel (Main Content):** Flexible width, for synchronization flow, diff viewing, and comparison controls.
* **Right Panel (Sidebar):** Fixed width, for file content preview.

### 3. Left Panel: Artifact Files Explorer

* **Header:** Title labeled "Artifact Files".
* **Search Input:** A search bar below the header with a magnifying glass icon and placeholder text "Search...".
* **File Tree View:** A hierarchical list representing the directory structure of the artifact.
  * Folders can be expanded/collapsed.
  * Files show their extension icons (e.g., markdown, python).
* **Status Indicators:** To the right of each file name, a status icon indicates its state relative to the comparison baseline:
  * **Blue Dot (Modified):** Indicates the file has changes that need syncing.
  * **Green Checkmark (Synced):** Indicates the file is currently in sync.
* **Interaction:** Clicking a file in this tree updates the contents of the Middle (Diff Viewer) and Right (Preview) panels.

### 4. Top Banner: Artifact Flow Visualization

Located above the three-panel layout, this banner visualizes the state across the three tiers.

* **Three Nodes (Left to Right):**
  * **Node 1: SOURCE (Upstream):** Shows an icon (e.g., GitHub logo), current version, commit hash, and status message (e.g., "[v2.6.0, abc456... - New Update]").
  * **Node 2: COLLECTION (Personal Library):** Shows an icon (e.g., layered box), current version, and hash (e.g., "[v2.5.0, abc123...]").
  * **Node 3: PROJECT (Local):** Shows an icon (e.g., folder), current version, hash, and status (e.g., "[v2.5.0, xyz789... - Modified]"). The background of this node is highlighted (e.g., light orange) if it deviates from the collection.
* **Directional Action Buttons & Connectors:**
  * **Arrow 1 (Source to Collection):** A curved arrow overlaid with a blue action button labeled "Pull from Source".
  * **Arrow 2 (Collection to Project):** A curved arrow overlaid with a blue action button labeled "Deploy to Project".
  * **Arrow 3 (Project to Collection):** A curved arrow indicating the reverse flow, overlaid with a disabled/greyed-out button labeled "Push to Collection" (indicating future functionality).

### 5. Middle Panel: Comparison and Diff Viewer

* **Comparison Selectors:** A "Compare:" label followed by three dropdown menus allowing the user to define the comparison context:
  * Dropdown 1: Primary comparison scope (e.g., selected as "Collection vs. Project").
  * Dropdown 2 & 3: Quick selectors for other common scopes ("Source vs. Collection", "Source vs. Project").
* **Comparison Headers:** Below the selectors, two headers define the distinct views being compared based on the dropdown selection:
  * **Left Header:** e.g., "Collection Level (v2.5.0, abc123d...)".
  * **Right Header:** e.g., "Project Level (v2.5.0, xyz789a... - Modified)". Highlighted orange if modified.
* **Drift Alert Banner:** A prominent alert box (yellow/orange background with warning icon) displayed if the levels are out of sync. It contains:
  * Text: "Drift Detected".
  * Contextual Action Buttons: "View Diffs", "Merge...", "Take Upstream", "Keep Local".
* **Diff Viewer Container:**
  * **File Label:** Shows the name of the currently selected file from the file tree (e.g., "python_skill.py").
  * **Diff Toolbar:** Buttons for navigating changes ("Prev Change", "Next Change") and switching views ("Inline Diff", "Side-by-Side Diff" - currently active).
  * **Code View (Side-by-Side):** Two panes showing code with line numbers.
    * **Left Pane (Base Version):** Shows the original code. Deletions or changes are highlighted in red/pink background.
    * **Right Pane (Target Version):** Shows the modified code. Additions or changes are highlighted in green/light green background.

### 6. Right Panel: Content Preview

* **Header:** Title labeled "File Preview: [Selected File Name]".
* **Rendered Content View:** A read-only view displaying the rendered output of the selected file.
  * If a Markdown file is selected, it shows fully rendered HTML (headers, lists, code blocks).
  * It should reflect the state of the file in the "Project (Local)" tier.

### 7. Global Action Footer

Located at the very bottom of the modal.

* **Sync Actions Bar (Left Side):** A row of actionable buttons for performing artifact-level operations:
  * "Pull Collection Updates"
  * "Push Local Changes"
  * "Merge Conflicts"
  * "Resolve All"
* **Final Commit Buttons (Right Side):**
  * "Cancel" button (secondary style).
  * "Apply Sync Actions" button (primary blue style) to execute pending changes and close the modal.
