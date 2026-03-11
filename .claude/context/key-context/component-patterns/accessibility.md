# Accessibility Patterns

How to build accessible components with proper keyboard navigation, ARIA labels, and Radix UI patterns.

## ARIA Labels for Icon Buttons

Icon-only buttons must have accessible labels via `aria-label`:

```typescript
// ✅ CORRECT - Icon button with aria-label
import { Button } from '@/components/ui/button';
import { Trash2 as TrashIcon } from 'lucide-react';

<Button variant="ghost" size="icon" aria-label="Delete collection">
  <TrashIcon className="h-4 w-4" />
</Button>

// ✅ CORRECT - Icon button with text label (label provided by text)
<Button variant="ghost">
  <TrashIcon className="h-4 w-4" />
  <span className="ml-2">Delete</span>
</Button>

// ✅ CORRECT - Visually hidden text for screen readers
<Button variant="ghost" size="icon">
  <TrashIcon className="h-4 w-4" />
  <span className="sr-only">Delete collection</span>
</Button>

// ❌ WRONG - Icon button without label
<Button variant="ghost" size="icon">
  <TrashIcon className="h-4 w-4" />
</Button>
```

## Keyboard Navigation Patterns

### Radix UI Components (Dialog, Tabs, DropdownMenu)

Radix components provide built-in keyboard support. Always use them for complex patterns:

| Component | Built-in Keyboard Support |
|-----------|---------------------------|
| **Dialog** | ESC to close, focus trap, return focus on close |
| **Tabs** | Arrow keys, Home/End, roving tabindex |
| **DropdownMenu** | Arrow keys, ESC to close, typeahead support |
| **Checkbox** | Space to toggle, focus indicators |
| **RadioGroup** | Arrow keys, automatic focus management |

**Example with Dialog (automatic focus management):**
```typescript
import {
  Dialog,
  DialogTrigger,
  DialogContent,
  DialogHeader,
  DialogTitle,
  DialogDescription,
} from '@/components/ui/dialog';

export function AccessibleModal() {
  return (
    <Dialog>
      <DialogTrigger asChild>
        <Button>Open Modal</Button>
      </DialogTrigger>
      <DialogContent>
        {/* DialogTitle is required for screen readers */}
        <DialogHeader>
          <DialogTitle>Confirm Action</DialogTitle>
          <DialogDescription>
            This action cannot be undone.
          </DialogDescription>
        </DialogHeader>

        {/* Focus is trapped here, ESC closes automatically */}
        <div className="space-y-4">
          <p>Are you sure you want to proceed?</p>
          <div className="flex justify-end gap-2">
            <Button variant="outline">Cancel</Button>
            <Button variant="destructive">Confirm</Button>
          </div>
        </div>
      </DialogContent>
    </Dialog>
  );
}
```

### Custom Interactive Elements

For custom components (not Radix primitives), add keyboard support explicitly:

```typescript
// Custom clickable element with keyboard support
<div
  role="button"
  tabIndex={0}
  onClick={handleClick}
  onKeyDown={(e) => {
    if (e.key === 'Enter' || e.key === ' ') {
      e.preventDefault();
      handleClick();
    }
  }}
  className="cursor-pointer focus:outline-none focus:ring-2 focus:ring-ring"
>
  Custom Button
</div>

// Custom toggle with keyboard support
<div
  role="switch"
  tabIndex={0}
  aria-checked={isEnabled}
  onClick={() => setEnabled(!isEnabled)}
  onKeyDown={(e) => {
    if (e.key === ' ') {
      e.preventDefault();
      setEnabled(!isEnabled);
    }
  }}
  className="cursor-pointer focus:outline-none focus:ring-2 focus:ring-ring"
>
  {isEnabled ? 'Enabled' : 'Disabled'}
</div>
```

## Form Labels

Always associate labels with inputs:

```typescript
// ✅ CORRECT - Label with htmlFor
<div>
  <label htmlFor="name" className="text-sm font-medium">
    Name
  </label>
  <input id="name" type="text" placeholder="Enter name" />
</div>

// ❌ WRONG - Form input without label
<input type="text" placeholder="Enter name" />
```

## Radix UI Table Pattern (if used)

When building tables with interactive elements, use Radix primitives for row selection:

```typescript
// Table rows should be keyboard-navigable
// Use checkboxes for row selection
<Table>
  <TableBody>
    {items.map((item) => (
      <TableRow key={item.id}>
        <TableCell>
          <Checkbox
            checked={selected.includes(item.id)}
            onCheckedChange={() => handleSelect(item.id)}
            aria-label={`Select ${item.name}`}
          />
        </TableCell>
        <TableCell>{item.name}</TableCell>
      </TableRow>
    ))}
  </TableBody>
</Table>
```

## Screen Reader Testing

When building components, test with:
- **macOS**: VoiceOver (Cmd+F5)
- **Windows**: NVDA (free) or JAWS
- **Web**: axe DevTools browser extension

Key checklist:
- All interactive elements are keyboard accessible
- All buttons and links have accessible names
- Form fields have associated labels
- Images have alt text
- Color is not the only way to convey information
- Focus indicators are visible
