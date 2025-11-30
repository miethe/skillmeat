# DiscoveryBanner Usage Example

## Basic Integration in /manage Page

```tsx
// app/manage/page.tsx
'use client';

import { useState } from 'react';
import { useRouter } from 'next/navigation';
import { DiscoveryBanner, BulkImportModal } from '@/components/discovery';
import type { DiscoveredArtifact } from '@/components/discovery';
import { useQuery } from '@tanstack/react-query';
import { apiRequest } from '@/lib/api';

export default function ManagePage() {
  const router = useRouter();
  const [showImportModal, setShowImportModal] = useState(false);

  // Fetch discovered artifacts from API
  const { data: discoveredArtifacts = [], isLoading } = useQuery({
    queryKey: ['discovered-artifacts'],
    queryFn: async () => {
      return await apiRequest<DiscoveredArtifact[]>('/api/artifacts/discover');
    },
  });

  const handleImport = async (selected: DiscoveredArtifact[]) => {
    // Import selected artifacts
    await apiRequest('/api/artifacts/import', {
      method: 'POST',
      body: JSON.stringify({ artifacts: selected }),
    });

    // Refresh the page or update state
    router.refresh();
    setShowImportModal(false);
  };

  return (
    <div className="container mx-auto py-6">
      <h1 className="text-3xl font-bold mb-6">Manage Artifacts</h1>

      {/* Discovery Banner - only shows when artifacts are found */}
      {!isLoading && (
        <DiscoveryBanner
          discoveredCount={discoveredArtifacts.length}
          onReview={() => setShowImportModal(true)}
          dismissible={true}
        />
      )}

      {/* Rest of your manage page content */}
      <div className="mt-6">
        {/* Your artifact list, filters, etc. */}
      </div>

      {/* Bulk Import Modal */}
      <BulkImportModal
        artifacts={discoveredArtifacts}
        open={showImportModal}
        onClose={() => setShowImportModal(false)}
        onImport={handleImport}
      />
    </div>
  );
}
```

## With Custom Styling

```tsx
<DiscoveryBanner
  discoveredCount={discoveredArtifacts.length}
  onReview={() => setShowImportModal(true)}
  dismissible={true}
/>
```

## Non-dismissible Banner (Critical Notifications)

```tsx
<DiscoveryBanner
  discoveredCount={criticalArtifacts.length}
  onReview={() => router.push('/import')}
  dismissible={false}
/>
```

## With Analytics Tracking

```tsx
<DiscoveryBanner
  discoveredCount={discoveredArtifacts.length}
  onReview={() => {
    // Track user interaction
    trackEvent('discovery_banner_clicked', {
      count: discoveredArtifacts.length,
    });
    setShowImportModal(true);
  }}
  dismissible={true}
/>
```

## Server-Side Data Fetching (Next.js App Router)

```tsx
// app/manage/page.tsx
import { DiscoveryBannerClient } from '@/components/discovery/discovery-banner-client';
import { apiRequest } from '@/lib/api';

export default async function ManagePage() {
  // Fetch on server
  const discoveredArtifacts = await apiRequest<DiscoveredArtifact[]>(
    '/api/artifacts/discover'
  );

  return (
    <div className="container mx-auto py-6">
      <h1 className="text-3xl font-bold mb-6">Manage Artifacts</h1>

      {/* Client component wrapper */}
      <DiscoveryBannerClient
        discoveredCount={discoveredArtifacts.length}
      />

      {/* Rest of page */}
    </div>
  );
}
```

```tsx
// components/discovery/discovery-banner-client.tsx
'use client';

import { useState } from 'react';
import { useRouter } from 'next/navigation';
import { DiscoveryBanner } from './DiscoveryBanner';

interface Props {
  discoveredCount: number;
}

export function DiscoveryBannerClient({ discoveredCount }: Props) {
  const router = useRouter();

  return (
    <DiscoveryBanner
      discoveredCount={discoveredCount}
      onReview={() => router.push('/import')}
      dismissible={true}
    />
  );
}
```

## Testing Example

```tsx
// __tests__/components/discovery-banner.test.tsx
import { render, screen, fireEvent } from '@testing-library/react';
import { DiscoveryBanner } from '@/components/discovery';

describe('DiscoveryBanner', () => {
  it('displays correct artifact count', () => {
    const onReview = jest.fn();
    render(
      <DiscoveryBanner
        discoveredCount={5}
        onReview={onReview}
      />
    );

    expect(screen.getByText(/Found 5 Artifacts/i)).toBeInTheDocument();
  });

  it('handles singular artifact correctly', () => {
    const onReview = jest.fn();
    render(
      <DiscoveryBanner
        discoveredCount={1}
        onReview={onReview}
      />
    );

    expect(screen.getByText(/Found 1 Artifact/i)).toBeInTheDocument();
    expect(screen.queryByText(/Artifacts/i)).not.toBeInTheDocument();
  });

  it('calls onReview when button is clicked', () => {
    const onReview = jest.fn();
    render(
      <DiscoveryBanner
        discoveredCount={3}
        onReview={onReview}
      />
    );

    fireEvent.click(screen.getByText('Review & Import'));
    expect(onReview).toHaveBeenCalledTimes(1);
  });

  it('dismisses when close button is clicked', () => {
    const onReview = jest.fn();
    render(
      <DiscoveryBanner
        discoveredCount={2}
        onReview={onReview}
        dismissible={true}
      />
    );

    fireEvent.click(screen.getByLabelText('Close'));
    expect(screen.queryByText(/Found 2 Artifacts/i)).not.toBeInTheDocument();
  });

  it('hides dismiss button when dismissible is false', () => {
    const onReview = jest.fn();
    render(
      <DiscoveryBanner
        discoveredCount={2}
        onReview={onReview}
        dismissible={false}
      />
    );

    expect(screen.queryByLabelText('Close')).not.toBeInTheDocument();
    expect(screen.queryByText('Dismiss')).not.toBeInTheDocument();
  });

  it('does not render when count is zero', () => {
    const onReview = jest.fn();
    const { container } = render(
      <DiscoveryBanner
        discoveredCount={0}
        onReview={onReview}
      />
    );

    expect(container.firstChild).toBeNull();
  });
});
```
