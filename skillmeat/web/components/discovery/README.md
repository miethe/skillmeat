# Discovery Components

UI components for artifact discovery and import workflows in SkillMeat.

## Components

### DiscoveryBanner

A banner component that appears when artifacts are discovered, prompting users to review and import them.

#### Props

| Prop | Type | Required | Default | Description |
|------|------|----------|---------|-------------|
| `discoveredCount` | `number` | Yes | - | Number of artifacts discovered |
| `onReview` | `() => void` | Yes | - | Callback when user clicks Review & Import |
| `dismissible` | `boolean` | No | `true` | Whether the banner can be dismissed |

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
<DiscoveryBanner
  discoveredCount={3}
  onReview={handleReview}
  dismissible={false}
/>
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

## Directory Structure

```
components/discovery/
├── DiscoveryBanner.tsx  # Main banner component
├── index.ts             # Module exports
└── README.md            # This file
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
