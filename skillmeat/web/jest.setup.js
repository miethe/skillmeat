/**
 * Jest Setup File for SkillMeat Web Interface
 *
 * Configures the test environment, adds custom matchers,
 * and mocks global objects and modules
 */

// Import testing library matchers
import '@testing-library/jest-dom';

// Import jest-axe matchers for accessibility testing
import { toHaveNoViolations } from 'jest-axe';
expect.extend(toHaveNoViolations);

// Import TextEncoder/TextDecoder for Node.js environment
import { TextEncoder, TextDecoder } from 'util';

// Polyfill TextEncoder/TextDecoder for Node.js environment
global.TextEncoder = TextEncoder;
global.TextDecoder = TextDecoder;

// Mock window.matchMedia
Object.defineProperty(window, 'matchMedia', {
  writable: true,
  value: jest.fn().mockImplementation((query) => ({
    matches: false,
    media: query,
    onchange: null,
    addListener: jest.fn(), // Deprecated
    removeListener: jest.fn(), // Deprecated
    addEventListener: jest.fn(),
    removeEventListener: jest.fn(),
    dispatchEvent: jest.fn(),
  })),
});

// Mock IntersectionObserver
global.IntersectionObserver = class IntersectionObserver {
  constructor() {}
  disconnect() {}
  observe() {}
  takeRecords() {
    return [];
  }
  unobserve() {}
};

// Mock ResizeObserver
global.ResizeObserver = class ResizeObserver {
  constructor() {}
  disconnect() {}
  observe() {}
  unobserve() {}
};

// Mock next/navigation
jest.mock('next/navigation', () => ({
  useRouter() {
    return {
      push: jest.fn(),
      replace: jest.fn(),
      prefetch: jest.fn(),
      back: jest.fn(),
      forward: jest.fn(),
      refresh: jest.fn(),
      pathname: '/',
      query: {},
      asPath: '/',
    };
  },
  usePathname() {
    return '/';
  },
  useSearchParams() {
    return new URLSearchParams();
  },
  useParams() {
    return {};
  },
  useSelectedLayoutSegment() {
    return null;
  },
  useSelectedLayoutSegments() {
    return [];
  },
  redirect: jest.fn(),
  notFound: jest.fn(),
}));

// Mock next/headers
jest.mock('next/headers', () => ({
  cookies() {
    return {
      get: jest.fn(),
      set: jest.fn(),
      delete: jest.fn(),
      has: jest.fn(),
      getAll: jest.fn(),
    };
  },
  headers() {
    return {
      get: jest.fn(),
      has: jest.fn(),
      forEach: jest.fn(),
      entries: jest.fn(),
      keys: jest.fn(),
      values: jest.fn(),
    };
  },
}));

// Mock environment variables
process.env.NEXT_PUBLIC_API_URL = 'http://localhost:8080';
process.env.NEXT_PUBLIC_WS_URL = 'ws://localhost:8080';
process.env.NODE_ENV = 'test';

// Suppress console errors/warnings in tests (optional)
// Uncomment if you want cleaner test output
// global.console = {
//   ...console,
//   error: jest.fn(),
//   warn: jest.fn(),
// }

// Add custom matchers if needed
expect.extend({
  toBeValidUrl(received) {
    try {
      new URL(received);
      return {
        message: () => `expected ${received} not to be a valid URL`,
        pass: true,
      };
    } catch (error) {
      return {
        message: () => `expected ${received} to be a valid URL`,
        pass: false,
      };
    }
  },
});

// Clean up after each test
afterEach(() => {
  jest.clearAllMocks();
});
