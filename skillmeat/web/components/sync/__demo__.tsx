/**
 * Visual demonstration of ChangeBadge variants
 *
 * This file is for development/testing only.
 * Usage: Import in a test page or Storybook story.
 */

'use client';

import { ChangeBadge } from './ChangeBadge';

export function ChangeBadgeDemo() {
  return (
    <div className="space-y-8 p-8">
      <section>
        <h2 className="mb-4 text-xl font-bold">All Origins (Medium Size)</h2>
        <div className="flex flex-wrap gap-3">
          <ChangeBadge origin="upstream" />
          <ChangeBadge origin="local" />
          <ChangeBadge origin="both" />
          <ChangeBadge origin="none" />
        </div>
      </section>

      <section>
        <h2 className="mb-4 text-xl font-bold">Size Variants (Upstream)</h2>
        <div className="flex flex-wrap items-center gap-3">
          <ChangeBadge origin="upstream" size="sm" />
          <ChangeBadge origin="upstream" size="md" />
          <ChangeBadge origin="upstream" size="lg" />
        </div>
      </section>

      <section>
        <h2 className="mb-4 text-xl font-bold">Icon Only (No Label)</h2>
        <div className="flex flex-wrap gap-3">
          <ChangeBadge origin="upstream" showLabel={false} />
          <ChangeBadge origin="local" showLabel={false} />
          <ChangeBadge origin="both" showLabel={false} />
          <ChangeBadge origin="none" showLabel={false} />
        </div>
      </section>

      <section>
        <h2 className="mb-4 text-xl font-bold">All Sizes x All Origins</h2>
        <div className="space-y-4">
          <div>
            <h3 className="mb-2 text-sm font-semibold">Small</h3>
            <div className="flex flex-wrap gap-2">
              <ChangeBadge origin="upstream" size="sm" />
              <ChangeBadge origin="local" size="sm" />
              <ChangeBadge origin="both" size="sm" />
              <ChangeBadge origin="none" size="sm" />
            </div>
          </div>
          <div>
            <h3 className="mb-2 text-sm font-semibold">Medium</h3>
            <div className="flex flex-wrap gap-2">
              <ChangeBadge origin="upstream" size="md" />
              <ChangeBadge origin="local" size="md" />
              <ChangeBadge origin="both" size="md" />
              <ChangeBadge origin="none" size="md" />
            </div>
          </div>
          <div>
            <h3 className="mb-2 text-sm font-semibold">Large</h3>
            <div className="flex flex-wrap gap-2">
              <ChangeBadge origin="upstream" size="lg" />
              <ChangeBadge origin="local" size="lg" />
              <ChangeBadge origin="both" size="lg" />
              <ChangeBadge origin="none" size="lg" />
            </div>
          </div>
        </div>
      </section>

      <section className="dark">
        <h2 className="mb-4 text-xl font-bold text-white">Dark Mode</h2>
        <div className="flex flex-wrap gap-3 rounded bg-gray-900 p-4">
          <ChangeBadge origin="upstream" />
          <ChangeBadge origin="local" />
          <ChangeBadge origin="both" />
          <ChangeBadge origin="none" />
        </div>
      </section>

      <section>
        <h2 className="mb-4 text-xl font-bold">In Context (Artifact List)</h2>
        <div className="max-w-md space-y-2">
          {[
            { name: 'canvas-design', origin: 'upstream' as const },
            { name: 'document-analyzer', origin: 'local' as const },
            { name: 'git-helper', origin: 'both' as const },
            { name: 'code-review', origin: 'none' as const },
          ].map((artifact) => (
            <div
              key={artifact.name}
              className="flex items-center justify-between rounded border p-3 hover:bg-gray-50 dark:hover:bg-gray-800"
            >
              <span className="font-mono text-sm">{artifact.name}</span>
              <ChangeBadge origin={artifact.origin} size="sm" />
            </div>
          ))}
        </div>
      </section>
    </div>
  );
}
