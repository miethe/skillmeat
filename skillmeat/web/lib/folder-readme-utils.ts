import { CatalogEntry } from '@/types/marketplace';

/**
 * Extract README content from folder artifacts.
 *
 * Looks for README.md or readme.md files in the folder's direct artifacts
 * and extracts a summary (first paragraph or summary section).
 *
 * @param folderPath - The folder path to find README for
 * @param entries - All catalog entries to search
 * @returns Extracted summary string or null if no README found
 *
 * @example
 * ```ts
 * const readme = extractFolderReadme('plugins/dev-tools', catalogEntries);
 * // Returns: "A collection of development tools for..."
 * ```
 */
export function extractFolderReadme(folderPath: string, entries: CatalogEntry[]): string | null {
  // Validate inputs
  if (!folderPath || !entries || entries.length === 0) {
    return null;
  }

  // Normalize folder path
  const normalizedFolderPath = folderPath.replace(/\\/g, '/').trim();
  if (!normalizedFolderPath || normalizedFolderPath === '/') {
    return null;
  }

  // Look for README files directly in this folder
  // Path should be: folderPath/README.md or folderPath/readme.md
  const readmeEntry = entries.find((entry) => {
    if (!entry.path || typeof entry.path !== 'string') {
      return false;
    }

    const normalizedPath = entry.path.replace(/\\/g, '/').trim();

    // Check if this entry is directly in the folder (not in a subfolder)
    // Pattern: folderPath/filename.md
    if (!normalizedPath.startsWith(normalizedFolderPath + '/')) {
      return false;
    }

    // Extract the part after the folder path
    const remainder = normalizedPath.substring(normalizedFolderPath.length + 1);

    // Check if it's a direct child (no additional slashes)
    if (remainder.includes('/')) {
      return false;
    }

    // Check if filename is README.md (case-insensitive)
    return remainder.toLowerCase() === 'readme.md';
  });

  if (!readmeEntry) {
    return null;
  }

  // Try to extract content from the entry
  // CatalogEntry doesn't have a 'content' field in the type definition,
  // but check if it exists at runtime (may be added via metadata indexing)
  const content = (readmeEntry as any).content;

  if (content && typeof content === 'string') {
    return extractFirstParagraph(content);
  }

  // Fallback: check if there's metadata with description
  // This would come from frontmatter or other metadata sources
  const metadata = (readmeEntry as any).metadata;
  if (metadata && typeof metadata === 'object' && metadata.description) {
    return typeof metadata.description === 'string' ? metadata.description : null;
  }

  return null;
}

/**
 * Extract the first meaningful paragraph from markdown content.
 *
 * Skips headings, empty lines, and frontmatter.
 * Returns first paragraph of at least 20 characters.
 * Truncates at 300 characters with ellipsis if longer.
 *
 * @param content - Raw markdown content
 * @returns First paragraph or null if none found
 *
 * @example
 * ```ts
 * const markdown = `---
 * title: My Doc
 * ---
 * # Heading
 *
 * This is the first paragraph with meaningful content.
 *
 * This is the second paragraph.
 * `;
 * const paragraph = extractFirstParagraph(markdown);
 * // Returns: "This is the first paragraph with meaningful content."
 * ```
 */
export function extractFirstParagraph(content: string): string | null {
  if (!content || typeof content !== 'string') {
    return null;
  }

  // Strip YAML frontmatter (content between --- delimiters at start)
  let processedContent = content;
  const frontmatterMatch = /^---\s*\n([\s\S]*?)\n---\s*(\n|$)/;
  if (frontmatterMatch.test(content)) {
    processedContent = content.replace(frontmatterMatch, '');
  }

  // Split into lines
  const lines = processedContent.split('\n');

  // Find first meaningful paragraph
  let paragraphLines: string[] = [];
  let inParagraph = false;
  let inCodeBlock = false;

  for (const line of lines) {
    const trimmed = line.trim();

    // Handle code block delimiters
    if (trimmed.startsWith('```')) {
      inCodeBlock = !inCodeBlock;
      continue;
    }

    // Skip lines inside code blocks
    if (inCodeBlock) {
      continue;
    }

    // Skip empty lines
    if (trimmed === '') {
      // If we were building a paragraph, we've reached its end
      if (inParagraph && paragraphLines.length > 0) {
        break;
      }
      continue;
    }

    // Skip headings (lines starting with #)
    if (trimmed.startsWith('#')) {
      continue;
    }

    // Skip list items and other special markdown syntax
    if (
      trimmed.startsWith('-') ||
      trimmed.startsWith('*') ||
      trimmed.startsWith('>') ||
      trimmed.startsWith('|')
    ) {
      continue;
    }

    // This looks like paragraph content
    inParagraph = true;
    paragraphLines.push(trimmed);
  }

  // Join paragraph lines
  if (paragraphLines.length === 0) {
    return null;
  }

  const paragraph = paragraphLines.join(' ').trim();

  // Check minimum length requirement
  if (paragraph.length < 20) {
    return null;
  }

  // Truncate at 300 characters with ellipsis
  if (paragraph.length > 300) {
    return paragraph.substring(0, 297) + '...';
  }

  return paragraph;
}
