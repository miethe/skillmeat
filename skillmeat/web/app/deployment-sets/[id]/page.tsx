import { Suspense } from 'react';
import { Skeleton } from '@/components/ui/skeleton';
import { DeploymentSetDetailClient } from './deployment-set-detail-client';

export const metadata = {
  title: 'Deployment Set Detail | SkillMeat',
  description: 'View and manage a deployment set',
};

/**
 * Deployment Set Detail Page
 *
 * Server component shell that unwraps the dynamic [id] param and
 * renders the interactive client component inside a Suspense boundary.
 *
 * Next.js 15: params is a Promise — await before use.
 */
export default async function DeploymentSetDetailPage({
  params,
}: {
  params: Promise<{ id: string }>;
}) {
  const { id } = await params;

  return (
    <div className="container mx-auto py-6">
      <Suspense fallback={<DeploymentSetDetailSkeleton />}>
        <DeploymentSetDetailClient id={id} />
      </Suspense>
    </div>
  );
}

function DeploymentSetDetailSkeleton() {
  return (
    <div className="space-y-6">
      {/* Back button skeleton */}
      <Skeleton className="h-9 w-32" />

      {/* Header card skeleton */}
      <div className="rounded-lg border bg-card p-6 space-y-4">
        <div className="flex items-center gap-3">
          <Skeleton className="h-8 w-8 rounded-full" />
          <Skeleton className="h-8 w-64" />
          <Skeleton className="h-8 w-24 ml-auto" />
        </div>
        <Skeleton className="h-4 w-96" />
        <div className="flex gap-2">
          <Skeleton className="h-6 w-16 rounded-full" />
          <Skeleton className="h-6 w-20 rounded-full" />
        </div>
      </div>

      {/* Stats bar skeleton */}
      <div className="flex gap-6">
        <Skeleton className="h-5 w-28" />
        <Skeleton className="h-5 w-32" />
      </div>

      {/* Member list skeleton */}
      <div className="space-y-2">
        {[1, 2, 3].map((i) => (
          <Skeleton key={i} className="h-14 w-full rounded-lg" />
        ))}
      </div>
    </div>
  );
}
