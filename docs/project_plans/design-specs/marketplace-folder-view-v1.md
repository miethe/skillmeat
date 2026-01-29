# Marketplace Folder View v1 Design Specification

**Author:** Gemini

### 1. Design Principles

* **Semantic Hierarchy over File Structure:** Users should navigate by meaningful categories (e.g., "Productivity Tools"), not raw file paths (e.g., `src/main/plugins/productivity`).
* **Signal over Noise:** Automatically hide root containers (e.g., `plugins/`, `src/`) and leaf artifact containers (e.g., `commands/`, `agents/`) from the navigation tree.
* **Group Context:** Artifacts that belong together (a "suite" of tools) should be displayed together on a single page, grouped by their specific type.
* **Efficient Action:** Enable users to import an entire suite of tools with one click, rather than importing files individually.
* **Consistency:** Retain the existing SkillMeat design language (typography, color palette, component styles, iconography) for a seamless experience.

---

### 2. User Experience Flow

1. **Landing:** When a user clicks on a Source (e.g., "jeremylongshore/claude-code..."), they land on this new explorer view.
2. **Auto-Selection:** Upon loading, the "Semantic Tree" on the left automatically selects the first meaningful folder, populating the main content area on the right.
3. **Browsing:** The user navigates the tree on the left. Clicking a folder updates the right-hand pane to show context for that specific folder suite.
4. **Evaluation:** The right pane presents a summary of the suite and lists all contained artifacts, grouped by type (Agents, Commands, etc.), using the familiar card layout for quick evaluation (confidence score, "New" status).
5. **Action:** The user can either "Import All" artifacts in the currently viewed suite or import individual artifacts via their respective cards.

---

### 3. Layout Structure & Wireframe

The page utilizes a standard **Master-Detail (Two-Pane)** interface within the existing application shell.

#### Global Elements (Retained from existing design)

* **Top Nav & Sidebar:** Standard SkillMeat application navigation remains unchanged.
* **Source Header:** Breadcrumbs (`<- Back to Sources`), Source Title, Branch/Tags, and Source-level stats (imported/excluded counts) remain at the top.
* **Global Filters:** The filter bar (Search, Types, Sort, Confidence Range, etc.) remains below the header. *Note: Filtering should apply to the artifacts displayed within the currently selected folder in the right pane.*

#### The Two-Pane Content Area

| Left Pane: Semantic Tree (~25% Width) | Right Pane: Folder Detail View (~75% Width) |
| --- | --- |
| A hierarchical navigation component. | A dashboard view for the selected tree node. |
| **Behavior:** Acts as the primary filter for the right pane. Single-click selection. | **Behavior:** Displays grouped contents and metadata. |

---

### 4. Component Specifications

#### A. The Semantic Tree (Left Pane)

This is a specialized tree-view component.

* **Content Source:** derived from the repo directory structure.
* **Filtering Rules (The "Smart" part):**
* **Exclude Roots:** Do not display designated root folders (e.g., `plugins`, `src`).
* **Exclude Leafs:** Do not display designated artifact containers as expandable folders (e.g., `commands`, `agents`, `prompts`). These are handled in the right pane.
* **Show Intermediate:** Display directories that sit between roots and leafs (e.g., `Productivity`, `Vibe Guide`).


* **States:**
* *Default:* Folder icon + Folder Name.
* *Hover:* Light gray background fill.
* *Selected:* active purple/blue text color and/or background indicator to match existing branding.
* *Expanded/Collapsed:* Standard chevron indicators for nested folders.



#### B. Folder Detail Header (Right Pane Top)

Located at the top of the right pane, providing context for the selected suite.

* **Title:** Large header displaying the current folder name (e.g., "Vibe Guide").
* **Parent Metadata Chip:** A small chip located above or below the title indicating the parent category (e.g., icon + "Productivity").
* **Description:** A text block below the title.
* *Source:* Pulled from a `README.md` within that specific folder, or an AI-generated summary if none exists.


* **Primary Action (Bulk Import):** A prominent button (e.g., top right of this section, styled like the existing dark "Select All" style) labeled "Import All in [Folder Name]".
* *Action:* Triggers import for all artifacts listed below.



#### C. Artifact Groups (Right Pane Body)

The main content body organized by artifact type.

* **Section Headers:** Clear h3/h4 style headers for each artifact type discovered within the folder (e.g., "Agents", "Commands", "MCP Servers").
* **Artifact Cards:** Under each header, display the artifacts using the **existing SkillMeat card component**.
* *Layout:* A flexible grid or stacked list of cards depending on screen width.
* *Card Data:* Must include Icon (specific to type), Name, "New" badge (if applicable), Confidence Meter bar, and individual "Import" button with icon.
* *Interactivity:* Clicking the card body (not the import button) should open the detailed artifact modal.

