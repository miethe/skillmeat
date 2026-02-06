import { Suspense } from 'react';
import { MemoryPageContent } from './memory-page-content';
import { MemoryPageSkeleton } from './loading';

export default async function MemoryPage({ params }: { params: Promise<{ id: string }> }) {
  const { id } = await params;

  return (
    <Suspense fallback={<MemoryPageSkeleton />}>
      <MemoryPageContent projectId={id} />
    </Suspense>
  );
}
