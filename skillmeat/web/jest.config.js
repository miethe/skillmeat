const nextJest = require('next/jest');

/**
 * Jest Configuration for SkillMeat Web Interface
 *
 * Configures Jest for testing React components, hooks, and utilities
 * in the Next.js application
 */

const createJestConfig = nextJest({
  // Provide the path to your Next.js app to load next.config.js and .env files in your test environment
  dir: './',
});

// Add any custom config to be passed to Jest
const customJestConfig = {
  // Test environment
  testEnvironment: 'jsdom',

  // Setup files
  setupFilesAfterEnv: ['<rootDir>/jest.setup.js'],

  // Module name mapper for absolute imports and assets
  moduleNameMapper: {
    '^@/(.*)$': '<rootDir>/$1',
    '^@/app/(.*)$': '<rootDir>/app/$1',
    '^@/components/(.*)$': '<rootDir>/components/$1',
    '^@/hooks/(.*)$': '<rootDir>/hooks/$1',
    '^@/lib/(.*)$': '<rootDir>/lib/$1',
    '^@/sdk/(.*)$': '<rootDir>/sdk/$1',
    '^@/styles/(.*)$': '<rootDir>/styles/$1',
    // Handle CSS imports (with CSS modules)
    '^.+\\.module\\.(css|sass|scss)$': 'identity-obj-proxy',
    // Handle CSS imports (without CSS modules)
    '^.+\\.(css|sass|scss)$': '<rootDir>/__mocks__/styleMock.js',
    // Handle image imports
    '^.+\\.(jpg|jpeg|png|gif|webp|avif|svg)$': '<rootDir>/__mocks__/fileMock.js',
  },

  // Coverage collection
  collectCoverageFrom: [
    'app/**/*.{ts,tsx}',
    'components/**/*.{ts,tsx}',
    'hooks/**/*.{ts,tsx}',
    'lib/**/*.{ts,tsx}',
    'sdk/**/*.{ts,tsx}',
    '!**/*.d.ts',
    '!**/node_modules/**',
    '!**/.next/**',
    '!**/coverage/**',
    '!**/playwright-report/**',
    '!**/test-results/**',
    // Exclude generated SDK client code
    '!sdk/core/**',
    '!sdk/services/**',
    '!sdk/models/**',
    '!sdk/index.ts',
    // Exclude layout and template files (tested via E2E)
    '!app/layout.tsx',
    '!app/**/layout.tsx',
    '!app/**/template.tsx',
  ],

  // Coverage thresholds (note: singular "coverageThreshold", not "coverageThresholds")
  coverageThreshold: {
    global: {
      branches: 70,
      functions: 70,
      lines: 70,
      statements: 70,
    },
    // Stricter thresholds for critical paths
    'lib/auth/**/*.ts': {
      branches: 90,
      functions: 90,
      lines: 90,
      statements: 90,
    },
    'lib/api/**/*.ts': {
      branches: 80,
      functions: 80,
      lines: 80,
      statements: 80,
    },
  },

  // Test match patterns
  testMatch: ['**/__tests__/**/*.[jt]s?(x)', '**/?(*.)+(spec|test).[jt]s?(x)'],

  // Ignore patterns
  testPathIgnorePatterns: [
    '/node_modules/',
    '/.next/',
    '/tests/', // E2E tests are in tests/ directory
    '/playwright-report/',
    '/test-results/',
  ],

  // Transform patterns
  // Allow transformation of ESM modules like react-markdown
  transformIgnorePatterns: [
    '/node_modules/(?!(react-markdown|vfile|vfile-message|unist-.*|unified|bail|is-plain-obj|trough|remark-.*|mdast-util-.*|micromark.*|decode-named-character-reference|character-entities|property-information|hast-util-whitespace|space-separated-tokens|comma-separated-tokens|react-markdown)/)',
    '^.+\\.module\\.(css|sass|scss)$',
  ],

  // Coverage reporters
  coverageReporters: ['text', 'lcov', 'html', 'json'],

  // Verbose output
  verbose: true,

  // Max workers
  maxWorkers: '50%',

  // Clear mocks between tests
  clearMocks: true,

  // Reset mocks between tests
  resetMocks: true,

  // Restore mocks between tests
  restoreMocks: true,
};

// createJestConfig is exported this way to ensure that next/jest can load the Next.js config which is async
module.exports = createJestConfig(customJestConfig);
