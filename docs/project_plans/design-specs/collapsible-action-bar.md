Here is the design specification for the **Collapsible Action Bar**. This implementation focuses on **progressive disclosure**—keeping the UI noise-free until the user explicitly needs to perform the deployment action.

Since you are already using **Radix UI** and **shadcn/ui**, we have the perfect primitives to build this without adding heavy external libraries.

### **1. Component Architecture**

We will utilize the **shadcn/ui `Collapsible**` component (which wraps Radix `Collapsible`). This ensures distinct separation between the "Trigger" (the bar state) and the "Content" (the inputs).

#### **The Stack**

* **Root:** `Collapsible` (Controlled or Uncontrolled state)
* **Trigger:** `CollapsibleTrigger` (The bottom bar header)
* **Content:** `CollapsibleContent` (The actual deploy controls)
* **Icons:** `Lucide React` (Standard with shadcn) - `ChevronUp` / `ChevronDown`

---

### **2. Visual Anatomy & Layout**

#### **A. The Container (The "Bar")**

* **Positioning:** Fixed or Sticky at the bottom of the modal.
* *Designer Note:* To avoid it overlapping content awkwardly, add `pb-[height]` to the main modal content, or ensure the modal body has `flex-1` and this bar sits in the footer slot.


* **Styling:**
* **Background:** `bg-background` (or slightly offset with `bg-muted/30` for contrast).
* **Border:** `border-t` using your standard `border-border` color to separate it from the main content.
* **Backdrop:** Optional `backdrop-blur-sm` if the content scrolls *behind* it, giving it a modern, glass-like feel.



#### **B. The Closed State (Idle)**

* **Height:** Compact (~48px - 56px).
* **Elements:**
* **Left:** Text Label: "CLI Deploy Command" (Typography: `text-sm font-medium`).
* **Right:** `ChevronUp` icon (muted color).
* **Interaction:** The entire bar should be the clickable `CollapsibleTrigger`. Hovering should slightly darken the background (`hover:bg-accent`) to signal affordance.



#### **C. The Open State (Active)**

* **Animation:** The content slides **up**.
* **Elements:**
* The Trigger remains visible but the icon rotates to `ChevronDown`.
* The Content reveals the `Select` (Basic Deploy) and the `Input` (Command string) with the `Copy` button.


* **Padding:** Add comfortable padding (`p-4`) inside the content area to let the inputs breathe.

---

### **3. Interaction & Motion**

Using Radix's built-in state handling, we can animate the height.

* **Transition:** Use a cubic-bezier for a "snappy" feel.
* *Tailwind:* `data-[state=open]:animate-collapsible-up` (You may need to define this keyframe in your `tailwind.config.js` if it's not standard in your shadcn setup, usually it's `slide-down`, we want the inverse feel here).


* **Keyboard Nav:** Since it's a `<button>`, it is automatically focusable. Enter/Space toggles it.

---

### **4. UX Refinement Notes**

* **Default State:** Default this to open, but remember state across all modals if the user closes it in a session.