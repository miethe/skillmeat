'use client';

import { useEffect, useRef } from 'react';
import { EditorState } from '@codemirror/state';
import { EditorView, keymap } from '@codemirror/view';
import { markdown } from '@codemirror/lang-markdown';
import { defaultKeymap, history, historyKeymap } from '@codemirror/commands';
import { cn } from '@/lib/utils';

// ============================================================================
// Types
// ============================================================================

export interface MarkdownEditorProps {
  initialContent: string;
  onChange: (content: string) => void;
  readOnly?: boolean;
  className?: string;
}

// ============================================================================
// Theme Extensions
// ============================================================================

/**
 * Light theme extension for CodeMirror
 */
const lightTheme = EditorView.theme(
  {
    '&': {
      backgroundColor: 'hsl(var(--background))',
      color: 'hsl(var(--foreground))',
      height: '100%',
    },
    '.cm-content': {
      caretColor: 'hsl(var(--foreground))',
      fontFamily: 'ui-monospace, SFMono-Regular, Menlo, Monaco, Consolas, monospace',
      fontSize: '14px',
      lineHeight: '1.6',
      padding: '16px',
    },
    '.cm-cursor, .cm-dropCursor': {
      borderLeftColor: 'hsl(var(--foreground))',
    },
    '&.cm-focused .cm-selectionBackground, .cm-selectionBackground, .cm-content ::selection': {
      backgroundColor: 'hsl(var(--accent))',
    },
    '.cm-activeLine': {
      backgroundColor: 'hsl(var(--accent) / 0.1)',
    },
    '.cm-gutters': {
      backgroundColor: 'hsl(var(--muted))',
      color: 'hsl(var(--muted-foreground))',
      border: 'none',
    },
    '.cm-activeLineGutter': {
      backgroundColor: 'hsl(var(--accent) / 0.1)',
    },
  },
  { dark: false }
);

/**
 * Dark theme extension for CodeMirror
 */
const darkTheme = EditorView.theme(
  {
    '&': {
      backgroundColor: 'hsl(var(--background))',
      color: 'hsl(var(--foreground))',
      height: '100%',
    },
    '.cm-content': {
      caretColor: 'hsl(var(--foreground))',
      fontFamily: 'ui-monospace, SFMono-Regular, Menlo, Monaco, Consolas, monospace',
      fontSize: '14px',
      lineHeight: '1.6',
      padding: '16px',
    },
    '.cm-cursor, .cm-dropCursor': {
      borderLeftColor: 'hsl(var(--foreground))',
    },
    '&.cm-focused .cm-selectionBackground, .cm-selectionBackground, .cm-content ::selection': {
      backgroundColor: 'hsl(var(--accent))',
    },
    '.cm-activeLine': {
      backgroundColor: 'hsl(var(--accent) / 0.1)',
    },
    '.cm-gutters': {
      backgroundColor: 'hsl(var(--muted))',
      color: 'hsl(var(--muted-foreground))',
      border: 'none',
    },
    '.cm-activeLineGutter': {
      backgroundColor: 'hsl(var(--accent) / 0.1)',
    },
  },
  { dark: true }
);

// ============================================================================
// Main Component
// ============================================================================

/**
 * MarkdownEditor - CodeMirror 6 based markdown editor
 *
 * Features:
 * - Markdown syntax highlighting
 * - Basic keymaps (undo/redo, etc.)
 * - Theme support (light/dark based on system preference)
 * - onChange callback for content changes
 * - ReadOnly mode support
 * - Proper cleanup on unmount
 *
 * @example
 * ```tsx
 * <MarkdownEditor
 *   initialContent="# Hello World"
 *   onChange={(content) => setContent(content)}
 *   readOnly={false}
 * />
 * ```
 */
export function MarkdownEditor({
  initialContent,
  onChange,
  readOnly = false,
  className,
}: MarkdownEditorProps) {
  const containerRef = useRef<HTMLDivElement>(null);
  const editorRef = useRef<EditorView | null>(null);

  useEffect(() => {
    if (!containerRef.current) return;

    // Detect dark mode from system preference
    const isDarkMode = window.matchMedia('(prefers-color-scheme: dark)').matches;

    // Create editor state with all extensions
    const startState = EditorState.create({
      doc: initialContent,
      extensions: [
        // Language support
        markdown(),

        // History (undo/redo)
        history(),

        // Keymaps
        keymap.of([...defaultKeymap, ...historyKeymap]),

        // Update listener for onChange callback
        EditorView.updateListener.of((update) => {
          if (update.docChanged) {
            onChange(update.state.doc.toString());
          }
        }),

        // ReadOnly mode
        EditorView.editable.of(!readOnly),

        // Theme based on system preference
        isDarkMode ? darkTheme : lightTheme,

        // Line wrapping
        EditorView.lineWrapping,
      ],
    });

    // Create editor view
    const view = new EditorView({
      state: startState,
      parent: containerRef.current,
    });

    editorRef.current = view;

    // Cleanup on unmount
    return () => {
      view.destroy();
    };
  }, []); // Only run once on mount

  // Update content when initialContent changes externally
  useEffect(() => {
    if (editorRef.current && editorRef.current.state.doc.toString() !== initialContent) {
      editorRef.current.dispatch({
        changes: {
          from: 0,
          to: editorRef.current.state.doc.length,
          insert: initialContent,
        },
      });
    }
  }, [initialContent]);

  return (
    <div
      ref={containerRef}
      className={cn('h-full w-full overflow-auto border rounded-md', className)}
    />
  );
}
