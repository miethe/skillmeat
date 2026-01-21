# Discovery Components

UI components for artifact discovery and import workflows in SkillMeat.

## Components

### DiscoveryBanner

A banner component that appears when artifacts are discovered, prompting users to review and import them.

#### Props

| Prop              | Type         | Required | Default | Description                               |
| ----------------- | ------------ | -------- | ------- | ----------------------------------------- |
| `discoveredCount` | `number`     | Yes      | -       | Number of artifacts discovered            |
| `onReview`        | `() => void` | Yes      | -       | Callback when user clicks Review & Import |
| `dismissible`     | `boolean`    | No       | `true`  | Whether the banner can be dismissed       |

#### Features

- **Conditional Rendering**: Returns null if dismissed or no artifacts
- **Accessibility**:
  - `role="status"` and `aria-live="polite"` for screen readers
  - `aria-hidden` on decorative icons
  - `aria-label` on close buttons
- **Dismissible**: Optional dismiss functionality with both button and X icon
- **Plural Handling**: Correct grammar for "1 Artifact" vs "N Artifacts"
- **shadcn/ui Components**: Uses Alert, Button from the UI library

#### Usage

```tsx
import { DiscoveryBanner } from '@/components/discovery';
import { useRouter } from 'next/navigation';

export function ManagePage() {
  const router = useRouter();
  const discoveredCount = 5; // From your data source

  return (
    <div className="container mx-auto py-6">
      <DiscoveryBanner
        discoveredCount={discoveredCount}
        onReview={() => router.push('/import')}
        dismissible={true}
      />

      {/* Rest of your page content */}
    </div>
  );
}
```

#### Example: Non-dismissible Banner

```tsx
<DiscoveryBanner discoveredCount={3} onReview={handleReview} dismissible={false} />
```

#### Example: With Custom Review Handler

```tsx
<DiscoveryBanner
  discoveredCount={10}
  onReview={() => {
    // Custom logic before navigation
    console.log('User clicked Review & Import');
    trackEvent('discovery_banner_review_clicked');
    router.push('/import');
  }}
/>
```

### SkipPreferencesList

A collapsible component that displays and manages artifacts marked to skip during discovery/import.

#### Props

| Prop           | Type                            | Required | Default | Description                             |
| -------------- | ------------------------------- | -------- | ------- | --------------------------------------- |
| `skipPrefs`    | `SkipPreference[]`              | Yes      | -       | Array of skip preferences to display    |
| `onRemoveSkip` | `(artifactKey: string) => void` | Yes      | -       | Callback when user un-skips an artifact |
| `onClearAll`   | `() => void`                    | Yes      | -       | Callback when user clears all skips     |
| `isLoading`    | `boolean`                       | No       | `false` | Whether actions are in progress         |

#### Features

- **Collapsible Accordion**: Shows/hides skip list with count badge
- **Per-Artifact Details**: Displays name, type badge, skip reason, and date
- **Un-skip Individual**: Remove single skip preference
- **Clear All**: Bulk clear with confirmation dialog
- **Empty State**: Message when no artifacts are skipped
- **Accessibility**:
  - Full keyboard navigation
  - ARIA attributes (aria-expanded, aria-controls, aria-label)
  - Screen reader support
- **Auto-collapse**: Collapses when empty
- **shadcn/ui Components**: Uses Collapsible, AlertDialog, Badge, Button

#### Usage

```tsx
import { SkipPreferencesList } from '@/components/discovery';
import { loadSkipPrefs, removeSkipPref, clearSkipPrefs } from '@/lib/skip-preferences';

export function DiscoveryTab() {
  const [skipPrefs, setSkipPrefs] = useState<SkipPreference[]>([]);
  const projectId = 'my-project-123';

  useEffect(() => {
    const prefs = loadSkipPrefs(projectId);
    setSkipPrefs(prefs);
  }, [projectId]);

  const handleRemoveSkip = (artifactKey: string) => {
    removeSkipPref(projectId, artifactKey);
    setSkipPrefs(loadSkipPrefs(projectId));
  };

  const handleClearAll = () => {
    clearSkipPrefs(projectId);
    setSkipPrefs([]);
  };

  return (
    <div className="space-y-4">
      {/* Other discovery content */}
      <SkipPreferencesList
        skipPrefs={skipPrefs}
        onRemoveSkip={handleRemoveSkip}
        onClearAll={handleClearAll}
      />
    </div>
  );
}
```

#### Example: With Loading State

```tsx
<SkipPreferencesList
  skipPrefs={skipPrefs}
  onRemoveSkip={handleRemoveSkip}
  onClearAll={handleClearAll}
  isLoading={true}
/>
```

#### Example: With Toast Notifications

```tsx
const handleRemoveSkip = async (artifactKey: string) => {
  const success = removeSkipPref(projectId, artifactKey);
  if (success) {
    setSkipPrefs(loadSkipPrefs(projectId));
    toast.success('Artifact un-skipped successfully');
  }
};

const handleClearAll = () => {
  const count = skipPrefs.length;
  clearSkipPrefs(projectId);
  setSkipPrefs([]);
  toast.success(`Cleared ${count} skip preferences`);
};
```

## Directory Structure

```
components/discovery/
├── DiscoveryBanner.tsx               # Discovery alert banner
├── SkipPreferencesList.tsx           # Skip management component
├── SkipPreferencesList.example.tsx   # Usage examples
├── BulkImportModal.tsx               # Bulk import modal
├── AutoPopulationForm.tsx            # GitHub metadata form
├── ParameterEditorModal.tsx          # Parameter editing modal
├── DiscoveryTab.tsx                  # Main discovery tab
├── ArtifactActions.tsx               # Artifact action buttons
├── skeletons.tsx                     # Loading skeletons
├── index.ts                          # Module exports
├── USAGE_EXAMPLE.md                  # Usage documentation
└── README.md                         # This file
```

## Testing

The component is designed to be easily testable:

```tsx
import { render, screen, fireEvent } from '@testing-library/react';
import { DiscoveryBanner } from './DiscoveryBanner';

describe('DiscoveryBanner', () => {
  it('displays correct count', () => {
    const onReview = jest.fn();
    render(<DiscoveryBanner discoveredCount={5} onReview={onReview} />);
    expect(screen.getByText(/Found 5 Artifacts/i)).toBeInTheDocument();
  });

  it('calls onReview when button clicked', () => {
    const onReview = jest.fn();
    render(<DiscoveryBanner discoveredCount={3} onReview={onReview} />);
    fireEvent.click(screen.getByText('Review & Import'));
    expect(onReview).toHaveBeenCalledTimes(1);
  });

  it('dismisses when close button clicked', () => {
    const onReview = jest.fn();
    render(<DiscoveryBanner discoveredCount={2} onReview={onReview} />);
    fireEvent.click(screen.getByLabelText('Close'));
    expect(screen.queryByText(/Found 2 Artifacts/i)).not.toBeInTheDocument();
  });
});
```
