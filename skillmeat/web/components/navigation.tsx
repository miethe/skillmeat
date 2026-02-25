'use client';

import Link from 'next/link';
import { usePathname } from 'next/navigation';
import { cn } from '@/lib/utils';
import {
  LayoutDashboard,
  FolderOpen,
  Library,
  Layers,
  Layers3,
  Activity,
  FolderKanban,
  Brain,
  Server,
  Store,
  GitBranch,
  Share2,
  Settings,
  Tag,
  FileText,
  FileCode2,
  Github,
  Book,
} from 'lucide-react';
import { NavSection } from './nav-section';
import { CollectionSwitcherWithDialogs } from './collection/collection-switcher-with-dialogs';
import { useFeatureFlags } from '@/hooks';
import type { LucideIcon } from 'lucide-react';

// ============================================================================
// Types
// ============================================================================

interface NavItem {
  name: string;
  href: string;
  icon: LucideIcon;
}

interface NavSectionConfig {
  title: string;
  icon: LucideIcon;
  storageKey: string;
  defaultExpanded?: boolean;
  items: NavItem[];
}

interface NavigationConfig {
  topItems: NavItem[];
  sections: NavSectionConfig[];
  bottomItems: NavItem[];
}

// ============================================================================
// Static Navigation Configuration
// ============================================================================
// Items that are always visible regardless of feature flags.
// Feature-flagged items are injected at render time via buildNavigationConfig().

const BASE_COLLECTIONS_ITEMS: NavItem[] = [
  { name: 'Collections', href: '/collection', icon: Library },
  { name: 'Groups', href: '/groups', icon: Layers },
  // Deployment Sets item is conditionally inserted here when the flag is ON
  { name: 'Health & Sync', href: '/manage', icon: Activity },
  { name: 'MCP Servers', href: '/mcp', icon: Server },
];

const DEPLOYMENT_SETS_ITEM: NavItem = {
  name: 'Deployment Sets',
  href: '/deployment-sets',
  icon: Layers3,
};

const BASE_NAV_CONFIG = {
  topItems: [{ name: 'Dashboard', href: '/', icon: LayoutDashboard }],
  projectItems: [
    { name: 'Projects', href: '/projects', icon: FolderKanban },
    { name: 'Memories', href: '/memories', icon: Brain },
  ],
  marketplaceItems: [{ name: 'Sources', href: '/marketplace/sources', icon: GitBranch }],
  agentContextItems: [
    { name: 'Context Entities', href: '/context-entities', icon: FileCode2 },
    { name: 'Templates', href: '/templates', icon: FileText },
  ],
  resourcesItems: [
    { name: 'GitHub', href: 'https://github.com/miethe/skillmeat', icon: Github },
    { name: 'Documentation', href: 'https://github.com/miethe/skillmeat#readme', icon: Book },
  ],
  settingsItems: [
    { name: 'General', href: '/settings', icon: Settings },
    { name: 'Tags', href: '/settings/tags', icon: Tag },
  ],
  bottomItems: [{ name: 'Sharing', href: '/sharing', icon: Share2 }],
};

/**
 * Build the full navigation config, injecting feature-flagged items.
 *
 * Deployment Sets is inserted between Groups and Health & Sync in the
 * Collections section when deploymentSetsEnabled is true.
 */
function buildNavigationConfig(deploymentSetsEnabled: boolean): NavigationConfig {
  const collectionsItems: NavItem[] = deploymentSetsEnabled
    ? [
        { name: 'Collections', href: '/collection', icon: Library },
        { name: 'Groups', href: '/groups', icon: Layers },
        DEPLOYMENT_SETS_ITEM,
        { name: 'Health & Sync', href: '/manage', icon: Activity },
        { name: 'MCP Servers', href: '/mcp', icon: Server },
      ]
    : BASE_COLLECTIONS_ITEMS;

  return {
    topItems: BASE_NAV_CONFIG.topItems,
    sections: [
      {
        title: 'Projects',
        icon: FolderKanban,
        storageKey: 'projects',
        defaultExpanded: true,
        items: BASE_NAV_CONFIG.projectItems,
      },
      {
        title: 'Collections',
        icon: FolderOpen,
        storageKey: 'collections',
        defaultExpanded: true,
        items: collectionsItems,
      },
      {
        title: 'Marketplace',
        icon: Store,
        storageKey: 'marketplace',
        items: BASE_NAV_CONFIG.marketplaceItems,
      },
      {
        title: 'Agent Context',
        icon: FileText,
        storageKey: 'agent-context',
        items: BASE_NAV_CONFIG.agentContextItems,
      },
      {
        title: 'Resources',
        icon: Book,
        storageKey: 'resources',
        items: BASE_NAV_CONFIG.resourcesItems,
      },
      {
        title: 'Settings',
        icon: Settings,
        storageKey: 'settings',
        items: BASE_NAV_CONFIG.settingsItems,
      },
    ],
    bottomItems: BASE_NAV_CONFIG.bottomItems,
  };
}

// ============================================================================
// Main Component
// ============================================================================

/**
 * Navigation - Sidebar navigation component
 *
 * Provides hierarchical navigation with collapsible sections.
 * Supports:
 * - Top-level items (always visible)
 * - Collapsible sections with nested items
 * - Bottom-level items (always visible)
 * - Active state highlighting
 * - Keyboard navigation
 * - localStorage persistence
 * - Feature-flag-gated nav items (deployment sets)
 */
export function Navigation() {
  const pathname = usePathname();
  const { deploymentSetsEnabled } = useFeatureFlags();

  const navigationConfig = buildNavigationConfig(deploymentSetsEnabled);

  return (
    <aside className="w-64 shrink-0 overflow-y-auto border-r bg-background">
      <nav className="space-y-1 p-4">
        {/* Collection Switcher */}
        <div className="mb-4">
          <CollectionSwitcherWithDialogs className="w-full" />
        </div>

        {/* Top Items */}
        {navigationConfig.topItems.map((item) => {
          const Icon = item.icon;
          const isActive =
            pathname === item.href || (item.href !== '/' && pathname.startsWith(`${item.href}/`));

          return (
            <Link
              key={item.href}
              href={item.href}
              className={cn(
                'flex items-center gap-3 rounded-lg px-3 py-2 text-sm font-medium transition-colors',
                isActive
                  ? 'bg-primary text-primary-foreground'
                  : 'text-muted-foreground hover:bg-secondary/50 hover:text-foreground',
                'focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2'
              )}
            >
              <Icon className="h-4 w-4" />
              {item.name}
            </Link>
          );
        })}

        {/* Collapsible Sections */}
        {navigationConfig.sections.map((section) => (
          <NavSection
            key={section.storageKey}
            title={section.title}
            icon={section.icon}
            items={section.items}
            defaultExpanded={section.defaultExpanded}
            storageKey={section.storageKey}
          />
        ))}

        {/* Bottom Items */}
        {navigationConfig.bottomItems.map((item) => {
          const Icon = item.icon;
          const isActive = pathname === item.href || pathname.startsWith(`${item.href}/`);

          return (
            <Link
              key={item.href}
              href={item.href}
              className={cn(
                'flex items-center gap-3 rounded-lg px-3 py-2 text-sm font-medium transition-colors',
                isActive
                  ? 'bg-primary text-primary-foreground'
                  : 'text-muted-foreground hover:bg-secondary/50 hover:text-foreground',
                'focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2'
              )}
            >
              <Icon className="h-4 w-4" />
              {item.name}
            </Link>
          );
        })}
      </nav>
    </aside>
  );
}
