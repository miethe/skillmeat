/**
 * Type declarations for jest-axe.
 *
 * jest-axe does not ship its own .d.ts files and @types/jest-axe is not
 * installed. This ambient declaration file provides the minimal types needed
 * for test files that import from 'jest-axe' and call
 * `expect(results).toHaveNoViolations()`.
 */

interface JestAxeResults {
  violations: Array<{
    id: string;
    impact?: string;
    description: string;
    help: string;
    helpUrl: string;
    nodes: unknown[];
  }>;
  passes: unknown[];
  incomplete: unknown[];
  inapplicable: unknown[];
}

declare module 'jest-axe' {
  export function axe(
    html: Element | string,
    options?: Record<string, unknown>
  ): Promise<JestAxeResults>;

  export const toHaveNoViolations: Record<string, unknown>;

  export function configureAxe(options?: Record<string, unknown>): typeof axe;
}

declare namespace jest {
  // eslint-disable-next-line @typescript-eslint/no-unused-vars
  interface Matchers<R, T = {}> {
    toHaveNoViolations(): R;
  }
}
