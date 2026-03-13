/**
 * SkillBOMCard — Backstage EntityPage card scaffold
 *
 * Fetches the SkillMeat IDP BOM-card endpoint and renders a compact summary
 * of artifact inventory, attestation coverage, and signature status.
 *
 * Payload contract: docs/dev/api/backstage-bom-card-contract.md
 * Endpoint: GET /api/v1/integrations/idp/bom-card/{project_id}
 *
 * NOTE: This is a minimal scaffold — full Backstage EntityPage integration
 * (importing from @backstage/* packages, wiring into plugin API, etc.) is
 * tracked as a follow-on task. This component uses plain React + inline
 * styles to stay dependency-free until the Backstage frontend package is
 * installed.
 */

import React, { useEffect, useReducer, useCallback } from 'react';

// ---------------------------------------------------------------------------
// Types — mirror BomCardResponse from docs/dev/api/backstage-bom-card-contract.md
// ---------------------------------------------------------------------------

export interface BomCardArtifactEntry {
  /** Artifact name, unique within its type */
  name: string;
  /** Artifact type: "skill" | "command" | "agent" | "hook" | "mcp" | etc. */
  type: string;
  /** Deployed/upstream version; null if not set */
  version: string | null;
  /** SHA-256 hex digest; empty string if unavailable */
  content_hash: string;
}

export interface BomCardResponse {
  project_id: string;
  snapshot_id: number;
  /** ISO-8601 UTC timestamp */
  generated_at: string;
  artifact_count: number;
  attestation_count: number;
  /** "signed" | "unsigned" */
  signature_status: string;
  artifacts: BomCardArtifactEntry[];
}

// ---------------------------------------------------------------------------
// Component props
// ---------------------------------------------------------------------------

export interface SkillBOMCardProps {
  /** SkillMeat project identifier (matches catalog-info.yaml project name or UUID) */
  projectId: string;
  /** Base URL of the SkillMeat API, e.g. "https://sam.internal" */
  apiBaseUrl: string;
  /**
   * Optional bearer token for authenticated requests.
   * When omitted the request is sent unauthenticated (valid for dev/local mode).
   */
  token?: string;
  /**
   * Maximum number of artifact rows to display in the compact list.
   * Defaults to 5.
   */
  maxArtifacts?: number;
}

// ---------------------------------------------------------------------------
// Internal state machine
// ---------------------------------------------------------------------------

type State =
  | { status: 'idle' }
  | { status: 'loading' }
  | { status: 'success'; data: BomCardResponse }
  | { status: 'error'; message: string };

type Action =
  | { type: 'FETCH_START' }
  | { type: 'FETCH_SUCCESS'; payload: BomCardResponse }
  | { type: 'FETCH_ERROR'; message: string };

function reducer(state: State, action: Action): State {
  switch (action.type) {
    case 'FETCH_START':
      return { status: 'loading' };
    case 'FETCH_SUCCESS':
      return { status: 'success', data: action.payload };
    case 'FETCH_ERROR':
      return { status: 'error', message: action.message };
    default:
      return state;
  }
}

// ---------------------------------------------------------------------------
// Helpers
// ---------------------------------------------------------------------------

/** Format an ISO-8601 timestamp into a human-readable relative string */
function formatRelative(isoString: string): string {
  try {
    const date = new Date(isoString);
    const diffMs = Date.now() - date.getTime();
    const diffMin = Math.floor(diffMs / 60_000);
    if (diffMin < 1) return 'just now';
    if (diffMin < 60) return `${diffMin}m ago`;
    const diffHr = Math.floor(diffMin / 60);
    if (diffHr < 24) return `${diffHr}h ago`;
    const diffDays = Math.floor(diffHr / 24);
    return `${diffDays}d ago`;
  } catch {
    return isoString;
  }
}

/** Truncate a content hash to an 8-char short-hash for display */
function shortHash(hash: string): string {
  if (!hash) return '—';
  return hash.slice(0, 8);
}

/**
 * Map an artifact type string to a compact badge color.
 * Consumers can override via CSS if needed.
 * Unknown types default to a neutral grey.
 */
const TYPE_COLORS: Record<string, string> = {
  skill: '#2563eb',
  command: '#7c3aed',
  agent: '#0891b2',
  hook: '#d97706',
  mcp: '#059669',
  composite: '#db2777',
  deployment_set: '#64748b',
};

function typeColor(artifactType: string): string {
  return TYPE_COLORS[artifactType] ?? '#64748b';
}

// ---------------------------------------------------------------------------
// Sub-components
// ---------------------------------------------------------------------------

function StatPill({
  label,
  value,
  accent,
}: {
  label: string;
  value: string | number;
  accent?: string;
}) {
  return (
    <div style={styles.statPill}>
      <span style={{ ...styles.statValue, color: accent ?? styles.statValue.color }}>
        {value}
      </span>
      <span style={styles.statLabel}>{label}</span>
    </div>
  );
}

function TypeBadge({ type }: { type: string }) {
  return (
    <span
      style={{
        ...styles.badge,
        backgroundColor: typeColor(type) + '18',
        color: typeColor(type),
        borderColor: typeColor(type) + '40',
      }}
    >
      {type}
    </span>
  );
}

function ArtifactRow({ artifact }: { artifact: BomCardArtifactEntry }) {
  return (
    <li style={styles.artifactRow} role="listitem">
      <TypeBadge type={artifact.type} />
      <span style={styles.artifactName}>{artifact.name}</span>
      <span style={styles.artifactVersion}>{artifact.version ?? 'unversioned'}</span>
      <span
        style={styles.artifactHash}
        title={artifact.content_hash || 'no hash'}
      >
        {shortHash(artifact.content_hash)}
      </span>
    </li>
  );
}

function LoadingState() {
  return (
    <div style={styles.centeredState} aria-label="Loading BOM data">
      <div style={styles.spinner} role="status" aria-hidden="true" />
      <span style={styles.stateText}>Loading BOM&hellip;</span>
    </div>
  );
}

function ErrorState({ message, onRetry }: { message: string; onRetry: () => void }) {
  return (
    <div style={styles.centeredState} role="alert">
      <span style={styles.errorIcon} aria-hidden="true">&#9888;</span>
      <span style={styles.stateText}>{message}</span>
      <button style={styles.retryButton} onClick={onRetry} type="button">
        Retry
      </button>
    </div>
  );
}

function EmptyState() {
  return (
    <div style={styles.centeredState}>
      <span style={styles.emptyIcon} aria-hidden="true">&#128230;</span>
      <span style={styles.stateText}>No BOM snapshot found for this project.</span>
      <span style={styles.emptyHint}>Run &ldquo;skillmeat bom generate&rdquo; to create one.</span>
    </div>
  );
}

// ---------------------------------------------------------------------------
// Main component
// ---------------------------------------------------------------------------

/**
 * SkillBOMCard — Backstage EntityPage card scaffold.
 *
 * Renders a compact summary of the latest SkillMeat Bill-of-Materials snapshot
 * for a given project. Designed to be embedded in a Backstage EntityPage layout.
 *
 * @example
 * ```tsx
 * <SkillBOMCard
 *   projectId="my-api-project"
 *   apiBaseUrl="https://sam.internal"
 *   token={backstageToken}
 * />
 * ```
 */
export function SkillBOMCard({
  projectId,
  apiBaseUrl,
  token,
  maxArtifacts = 5,
}: SkillBOMCardProps) {
  const [state, dispatch] = useReducer(reducer, { status: 'idle' });

  const fetchBom = useCallback(async () => {
    dispatch({ type: 'FETCH_START' });
    try {
      const url = `${apiBaseUrl.replace(/\/$/, '')}/api/v1/integrations/idp/bom-card/${encodeURIComponent(projectId)}`;
      const headers: HeadersInit = { Accept: 'application/json' };
      if (token) {
        headers['Authorization'] = `Bearer ${token}`;
      }

      const res = await fetch(url, { headers });

      if (res.status === 404) {
        dispatch({ type: 'FETCH_SUCCESS', payload: null as unknown as BomCardResponse });
        return;
      }

      if (!res.ok) {
        let detail = `HTTP ${res.status}`;
        try {
          const body = await res.json();
          if (body?.detail) detail = body.detail;
        } catch {
          // ignore parse errors
        }
        dispatch({ type: 'FETCH_ERROR', message: detail });
        return;
      }

      const data: BomCardResponse = await res.json();
      dispatch({ type: 'FETCH_SUCCESS', payload: data });
    } catch (err) {
      const message = err instanceof Error ? err.message : 'Unknown error';
      dispatch({ type: 'FETCH_ERROR', message });
    }
  }, [projectId, apiBaseUrl, token]);

  useEffect(() => {
    fetchBom();
  }, [fetchBom]);

  const visibleArtifacts =
    state.status === 'success' && state.data
      ? state.data.artifacts.slice(0, maxArtifacts)
      : [];

  const hiddenCount =
    state.status === 'success' && state.data
      ? Math.max(0, state.data.artifacts.length - maxArtifacts)
      : 0;

  return (
    <section style={styles.card} aria-label="SkillBOM Card">
      {/* Header */}
      <header style={styles.header}>
        <div style={styles.headerLeft}>
          <span style={styles.logoMark} aria-hidden="true">&#9678;</span>
          <h2 style={styles.title}>SkillBOM</h2>
        </div>
        {state.status === 'success' && state.data && (
          <span
            style={styles.timestamp}
            title={state.data.generated_at}
          >
            {formatRelative(state.data.generated_at)}
          </span>
        )}
      </header>

      {/* Body */}
      <div style={styles.body}>
        {state.status === 'loading' && <LoadingState />}

        {state.status === 'error' && (
          <ErrorState message={state.message} onRetry={fetchBom} />
        )}

        {state.status === 'success' && !state.data && <EmptyState />}

        {state.status === 'success' && state.data && (
          <>
            {/* Stats row */}
            <div style={styles.statsRow} role="list" aria-label="BOM statistics">
              <StatPill
                label="Artifacts"
                value={state.data.artifact_count}
                accent="#2563eb"
              />
              <StatPill
                label="Attested"
                value={`${state.data.attestation_count} / ${state.data.artifact_count}`}
                accent={
                  state.data.attestation_count === state.data.artifact_count &&
                  state.data.artifact_count > 0
                    ? '#059669'
                    : '#d97706'
                }
              />
              <StatPill
                label="Signature"
                value={state.data.signature_status}
                accent={state.data.signature_status === 'signed' ? '#059669' : '#94a3b8'}
              />
              <StatPill label="Snapshot" value={`#${state.data.snapshot_id}`} />
            </div>

            {/* Artifact list */}
            {visibleArtifacts.length > 0 ? (
              <>
                <div style={styles.sectionLabel}>Artifacts</div>
                <ul style={styles.artifactList} role="list" aria-label="Artifact list">
                  {visibleArtifacts.map(artifact => (
                    <ArtifactRow
                      key={`${artifact.type}:${artifact.name}`}
                      artifact={artifact}
                    />
                  ))}
                </ul>
                {hiddenCount > 0 && (
                  <p style={styles.overflow}>
                    +{hiddenCount} more artifact{hiddenCount !== 1 ? 's' : ''} not shown
                  </p>
                )}
              </>
            ) : (
              <p style={styles.emptyHint}>No artifacts in this BOM snapshot.</p>
            )}
          </>
        )}
      </div>

      {/* Footer */}
      <footer style={styles.footer}>
        <span style={styles.footerText}>
          Project: <code style={styles.projectId}>{projectId}</code>
        </span>
        {state.status === 'success' && (
          <button
            style={styles.refreshButton}
            onClick={fetchBom}
            type="button"
            aria-label="Refresh BOM data"
          >
            &#8635; Refresh
          </button>
        )}
      </footer>
    </section>
  );
}

// ---------------------------------------------------------------------------
// Styles — Material UI-adjacent tokens, no external dependency
// ---------------------------------------------------------------------------

const styles = {
  card: {
    fontFamily:
      '"DM Sans", "Roboto", "Helvetica Neue", Arial, sans-serif',
    fontSize: '13px',
    lineHeight: 1.5,
    color: '#1e293b',
    background: '#ffffff',
    border: '1px solid #e2e8f0',
    borderRadius: '8px',
    boxShadow: '0 1px 3px rgba(0,0,0,0.08)',
    overflow: 'hidden',
    minWidth: '320px',
    maxWidth: '560px',
  } as React.CSSProperties,

  header: {
    display: 'flex',
    alignItems: 'center',
    justifyContent: 'space-between',
    padding: '12px 16px',
    borderBottom: '1px solid #f1f5f9',
    background: '#f8fafc',
  } as React.CSSProperties,

  headerLeft: {
    display: 'flex',
    alignItems: 'center',
    gap: '8px',
  } as React.CSSProperties,

  logoMark: {
    fontSize: '16px',
    color: '#2563eb',
  } as React.CSSProperties,

  title: {
    margin: 0,
    fontSize: '14px',
    fontWeight: 600,
    letterSpacing: '-0.01em',
    color: '#0f172a',
  } as React.CSSProperties,

  timestamp: {
    fontSize: '11px',
    color: '#94a3b8',
    fontVariantNumeric: 'tabular-nums',
  } as React.CSSProperties,

  body: {
    padding: '16px',
  } as React.CSSProperties,

  statsRow: {
    display: 'grid',
    gridTemplateColumns: 'repeat(4, 1fr)',
    gap: '8px',
    marginBottom: '16px',
  } as React.CSSProperties,

  statPill: {
    display: 'flex',
    flexDirection: 'column' as const,
    alignItems: 'center',
    padding: '8px 4px',
    background: '#f8fafc',
    borderRadius: '6px',
    border: '1px solid #e2e8f0',
    gap: '2px',
  } as React.CSSProperties,

  statValue: {
    fontSize: '15px',
    fontWeight: 700,
    color: '#1e293b',
    fontVariantNumeric: 'tabular-nums',
    lineHeight: 1.2,
  } as React.CSSProperties,

  statLabel: {
    fontSize: '10px',
    color: '#94a3b8',
    textTransform: 'uppercase' as const,
    letterSpacing: '0.06em',
  } as React.CSSProperties,

  sectionLabel: {
    fontSize: '10px',
    fontWeight: 600,
    textTransform: 'uppercase' as const,
    letterSpacing: '0.08em',
    color: '#94a3b8',
    marginBottom: '6px',
  } as React.CSSProperties,

  artifactList: {
    listStyle: 'none',
    margin: 0,
    padding: 0,
    display: 'flex',
    flexDirection: 'column' as const,
    gap: '4px',
  } as React.CSSProperties,

  artifactRow: {
    display: 'grid',
    gridTemplateColumns: '72px 1fr auto auto',
    alignItems: 'center',
    gap: '8px',
    padding: '6px 8px',
    borderRadius: '4px',
    background: '#f8fafc',
    border: '1px solid #f1f5f9',
  } as React.CSSProperties,

  badge: {
    display: 'inline-block',
    padding: '1px 6px',
    borderRadius: '4px',
    fontSize: '10px',
    fontWeight: 600,
    border: '1px solid transparent',
    letterSpacing: '0.02em',
    textAlign: 'center' as const,
    whiteSpace: 'nowrap' as const,
    overflow: 'hidden',
    textOverflow: 'ellipsis',
    maxWidth: '72px',
  } as React.CSSProperties,

  artifactName: {
    fontWeight: 500,
    color: '#334155',
    overflow: 'hidden',
    textOverflow: 'ellipsis',
    whiteSpace: 'nowrap' as const,
  } as React.CSSProperties,

  artifactVersion: {
    fontSize: '11px',
    color: '#94a3b8',
    whiteSpace: 'nowrap' as const,
  } as React.CSSProperties,

  artifactHash: {
    fontSize: '11px',
    color: '#cbd5e1',
    fontFamily: '"JetBrains Mono", "Fira Code", ui-monospace, monospace',
    whiteSpace: 'nowrap' as const,
  } as React.CSSProperties,

  overflow: {
    margin: '6px 0 0',
    fontSize: '11px',
    color: '#94a3b8',
    textAlign: 'center' as const,
  } as React.CSSProperties,

  centeredState: {
    display: 'flex',
    flexDirection: 'column' as const,
    alignItems: 'center',
    justifyContent: 'center',
    gap: '8px',
    padding: '24px 16px',
    textAlign: 'center' as const,
  } as React.CSSProperties,

  stateText: {
    color: '#64748b',
    fontSize: '13px',
  } as React.CSSProperties,

  emptyHint: {
    fontSize: '11px',
    color: '#94a3b8',
    margin: '4px 0 0',
  } as React.CSSProperties,

  emptyIcon: {
    fontSize: '28px',
  } as React.CSSProperties,

  errorIcon: {
    fontSize: '24px',
    color: '#ef4444',
  } as React.CSSProperties,

  spinner: {
    width: '24px',
    height: '24px',
    border: '2px solid #e2e8f0',
    borderTopColor: '#2563eb',
    borderRadius: '50%',
    animation: 'skillbom-spin 0.7s linear infinite',
  } as React.CSSProperties,

  retryButton: {
    marginTop: '4px',
    padding: '4px 12px',
    fontSize: '12px',
    fontWeight: 500,
    color: '#2563eb',
    background: 'transparent',
    border: '1px solid #93c5fd',
    borderRadius: '4px',
    cursor: 'pointer',
  } as React.CSSProperties,

  footer: {
    display: 'flex',
    alignItems: 'center',
    justifyContent: 'space-between',
    padding: '8px 16px',
    borderTop: '1px solid #f1f5f9',
    background: '#f8fafc',
  } as React.CSSProperties,

  footerText: {
    fontSize: '11px',
    color: '#94a3b8',
  } as React.CSSProperties,

  projectId: {
    fontFamily: '"JetBrains Mono", "Fira Code", ui-monospace, monospace',
    fontSize: '10px',
    color: '#64748b',
    background: '#f1f5f9',
    padding: '1px 4px',
    borderRadius: '3px',
  } as React.CSSProperties,

  refreshButton: {
    padding: '2px 8px',
    fontSize: '11px',
    fontWeight: 500,
    color: '#64748b',
    background: 'transparent',
    border: '1px solid #e2e8f0',
    borderRadius: '4px',
    cursor: 'pointer',
  } as React.CSSProperties,
};

// ---------------------------------------------------------------------------
// Spinner keyframe injection (no CSS file dependency)
// ---------------------------------------------------------------------------

if (typeof document !== 'undefined') {
  const styleId = 'skillbom-card-styles';
  if (!document.getElementById(styleId)) {
    const styleEl = document.createElement('style');
    styleEl.id = styleId;
    styleEl.textContent = `
      @keyframes skillbom-spin {
        to { transform: rotate(360deg); }
      }
    `;
    document.head.appendChild(styleEl);
  }
}

export default SkillBOMCard;
