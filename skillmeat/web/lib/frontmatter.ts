/**
 * Frontmatter parsing utility for YAML frontmatter in markdown files.
 *
 * Handles detection, parsing, and stripping of YAML frontmatter blocks
 * delimited by `---` markers at the start of content.
 *
 * NOTE: This implementation uses a simple YAML parser for common cases.
 * For production use with complex YAML, consider adding `yaml` or `js-yaml` package.
 */

/** Regex pattern to detect and capture frontmatter */
const FRONTMATTER_REGEX = /^---\r?\n([\s\S]*?)\r?\n---\r?\n?/;

/**
 * Detects whether content contains YAML frontmatter.
 *
 * Frontmatter must start at the beginning of the content with `---`
 * followed by a newline, and end with `---` followed by a newline.
 *
 * @param content - The string content to check
 * @returns true if frontmatter is present, false otherwise
 *
 * @example
 * ```ts
 * detectFrontmatter('---\ntitle: Hello\n---\nContent'); // true
 * detectFrontmatter('# Just markdown'); // false
 * detectFrontmatter(''); // false
 * ```
 */
export function detectFrontmatter(content: string): boolean {
  if (!content || typeof content !== 'string') {
    return false;
  }
  return FRONTMATTER_REGEX.test(content);
}

/**
 * Parses YAML frontmatter from content.
 *
 * Extracts the YAML block and returns both the parsed frontmatter object
 * and the remaining content with frontmatter stripped.
 *
 * @param content - The string content to parse
 * @returns Object containing frontmatter (null if invalid/missing) and clean content
 *
 * @example
 * ```ts
 * const result = parseFrontmatter('---\ntitle: Hello\nauthor: World\n---\nContent here');
 * // result.frontmatter = { title: 'Hello', author: 'World' }
 * // result.content = 'Content here'
 * ```
 */
export function parseFrontmatter(content: string): {
  frontmatter: Record<string, unknown> | null;
  content: string;
} {
  if (!content || typeof content !== 'string') {
    return { frontmatter: null, content: content || '' };
  }

  const match = content.match(FRONTMATTER_REGEX);

  if (!match) {
    return { frontmatter: null, content };
  }

  const yamlContent = match[1];
  const cleanContent = content.slice(match[0].length);

  try {
    const frontmatter = parseYaml(yamlContent);
    return { frontmatter, content: cleanContent };
  } catch (error) {
    console.warn(
      '[frontmatter] Failed to parse YAML frontmatter:',
      error instanceof Error ? error.message : String(error)
    );
    return { frontmatter: null, content: cleanContent };
  }
}

/**
 * Strips frontmatter from content, returning only the body.
 *
 * This is a convenience function when you only need the content
 * without the frontmatter metadata.
 *
 * @param content - The string content to process
 * @returns Content with frontmatter removed
 *
 * @example
 * ```ts
 * stripFrontmatter('---\ntitle: Hello\n---\nContent'); // 'Content'
 * stripFrontmatter('No frontmatter'); // 'No frontmatter'
 * ```
 */
export function stripFrontmatter(content: string): string {
  if (!content || typeof content !== 'string') {
    return content || '';
  }

  return content.replace(FRONTMATTER_REGEX, '');
}

/**
 * Simple YAML parser for frontmatter.
 *
 * Handles common frontmatter patterns:
 * - Key-value pairs (string, number, boolean, null)
 * - Arrays (inline [...] and block - item format)
 * - Nested objects (indentation-based)
 * - Quoted strings (single and double)
 * - Multi-line strings (limited support)
 *
 * @internal
 * @param yaml - Raw YAML string to parse
 * @returns Parsed object
 * @throws Error if YAML is malformed
 */
function parseYaml(yaml: string): Record<string, unknown> {
  if (!yaml.trim()) {
    return {};
  }

  const result: Record<string, unknown> = {};
  const lines = yaml.split(/\r?\n/);
  const stack: Array<{ obj: Record<string, unknown>; indent: number }> = [
    { obj: result, indent: -1 },
  ];
  let currentArrayKey: string | null = null;
  let currentArrayIndent = -1;

  for (let i = 0; i < lines.length; i++) {
    const line = lines[i];

    // Skip empty lines and comments
    if (!line.trim() || line.trim().startsWith('#')) {
      continue;
    }

    const indent = line.search(/\S/);
    const trimmedLine = line.trim();

    // Handle array items (- value)
    if (trimmedLine.startsWith('- ')) {
      if (currentArrayKey && indent > currentArrayIndent) {
        const arrayValue = trimmedLine.slice(2).trim();
        const target = stack[stack.length - 1].obj;
        const arr = target[currentArrayKey] as unknown[];
        arr.push(parseValue(arrayValue));
        continue;
      }
    }

    // Reset array context if indent changes
    if (indent <= currentArrayIndent) {
      currentArrayKey = null;
      currentArrayIndent = -1;
    }

    // Pop stack for decreased indent
    while (stack.length > 1 && indent <= stack[stack.length - 1].indent) {
      stack.pop();
    }

    // Parse key-value pair
    const colonIndex = trimmedLine.indexOf(':');
    if (colonIndex === -1) {
      continue;
    }

    const key = trimmedLine.slice(0, colonIndex).trim();
    const rawValue = trimmedLine.slice(colonIndex + 1).trim();

    if (!key) {
      continue;
    }

    const target = stack[stack.length - 1].obj;

    if (rawValue === '') {
      // Check if next line starts an array or nested object
      const nextLine = lines[i + 1];
      if (nextLine && nextLine.trim().startsWith('- ')) {
        // Array starting on next line
        target[key] = [];
        currentArrayKey = key;
        currentArrayIndent = indent;
      } else if (nextLine) {
        const nextIndent = nextLine.search(/\S/);
        if (nextIndent > indent && nextLine.includes(':')) {
          // Nested object
          const nested: Record<string, unknown> = {};
          target[key] = nested;
          stack.push({ obj: nested, indent });
        } else {
          target[key] = null;
        }
      } else {
        target[key] = null;
      }
    } else if (rawValue.startsWith('[') && rawValue.endsWith(']')) {
      // Inline array
      target[key] = parseInlineArray(rawValue);
    } else if (rawValue.startsWith('{') && rawValue.endsWith('}')) {
      // Inline object
      target[key] = parseInlineObject(rawValue);
    } else {
      target[key] = parseValue(rawValue);
    }
  }

  return result;
}

/**
 * Parse a single YAML value.
 * @internal
 */
function parseValue(value: string): unknown {
  if (!value) {
    return null;
  }

  // Handle quoted strings
  if (
    (value.startsWith('"') && value.endsWith('"')) ||
    (value.startsWith("'") && value.endsWith("'"))
  ) {
    return value.slice(1, -1);
  }

  // Handle booleans
  const lowerValue = value.toLowerCase();
  if (lowerValue === 'true' || lowerValue === 'yes' || lowerValue === 'on') {
    return true;
  }
  if (lowerValue === 'false' || lowerValue === 'no' || lowerValue === 'off') {
    return false;
  }

  // Handle null
  if (lowerValue === 'null' || lowerValue === '~') {
    return null;
  }

  // Handle numbers
  if (/^-?\d+$/.test(value)) {
    return parseInt(value, 10);
  }
  if (/^-?\d+\.\d+$/.test(value)) {
    return parseFloat(value);
  }

  // Handle ISO date strings (keep as string for now)
  // Return as-is string
  return value;
}

/**
 * Parse inline YAML array: [item1, item2, item3]
 * @internal
 */
function parseInlineArray(value: string): unknown[] {
  const inner = value.slice(1, -1).trim();
  if (!inner) {
    return [];
  }

  const items: unknown[] = [];
  let current = '';
  let depth = 0;
  let inQuote: string | null = null;

  for (let i = 0; i < inner.length; i++) {
    const char = inner[i];

    if (inQuote) {
      current += char;
      if (char === inQuote && inner[i - 1] !== '\\') {
        inQuote = null;
      }
      continue;
    }

    if (char === '"' || char === "'") {
      inQuote = char;
      current += char;
      continue;
    }

    if (char === '[' || char === '{') {
      depth++;
      current += char;
      continue;
    }

    if (char === ']' || char === '}') {
      depth--;
      current += char;
      continue;
    }

    if (char === ',' && depth === 0) {
      items.push(parseValue(current.trim()));
      current = '';
      continue;
    }

    current += char;
  }

  if (current.trim()) {
    items.push(parseValue(current.trim()));
  }

  return items;
}

/**
 * Parse inline YAML object: {key1: value1, key2: value2}
 * @internal
 */
function parseInlineObject(value: string): Record<string, unknown> {
  const inner = value.slice(1, -1).trim();
  if (!inner) {
    return {};
  }

  const result: Record<string, unknown> = {};
  let current = '';
  let depth = 0;
  let inQuote: string | null = null;

  const pairs: string[] = [];

  for (let i = 0; i < inner.length; i++) {
    const char = inner[i];

    if (inQuote) {
      current += char;
      if (char === inQuote && inner[i - 1] !== '\\') {
        inQuote = null;
      }
      continue;
    }

    if (char === '"' || char === "'") {
      inQuote = char;
      current += char;
      continue;
    }

    if (char === '[' || char === '{') {
      depth++;
      current += char;
      continue;
    }

    if (char === ']' || char === '}') {
      depth--;
      current += char;
      continue;
    }

    if (char === ',' && depth === 0) {
      pairs.push(current.trim());
      current = '';
      continue;
    }

    current += char;
  }

  if (current.trim()) {
    pairs.push(current.trim());
  }

  for (const pair of pairs) {
    const colonIndex = pair.indexOf(':');
    if (colonIndex !== -1) {
      const key = pair.slice(0, colonIndex).trim();
      const val = pair.slice(colonIndex + 1).trim();
      result[key] = parseValue(val);
    }
  }

  return result;
}
