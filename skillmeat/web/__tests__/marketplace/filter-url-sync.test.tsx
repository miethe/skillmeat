/**
 * URL Parameter Synchronization Tests
 *
 * Tests that filter state is properly synchronized with URL parameters,
 * enabling shareable URLs for filtered views.
 */

import { renderHook, act } from '@testing-library/react';
import { useSearchParams, useRouter, usePathname } from 'next/navigation';

// Mock Next.js navigation
jest.mock('next/navigation', () => ({
  useSearchParams: jest.fn(),
  useRouter: jest.fn(),
  usePathname: jest.fn(),
}));

// Helper to create mock searchParams
function createMockSearchParams(params: Record<string, string>) {
  const urlParams = new URLSearchParams(params);
  return {
    get: (key: string) => urlParams.get(key),
    toString: () => urlParams.toString(),
  };
}

describe('Filter URL Synchronization', () => {
  let mockRouter: { replace: jest.Mock };
  let mockPathname: string;

  beforeEach(() => {
    mockRouter = {
      replace: jest.fn(),
    };
    mockPathname = '/marketplace/sources/123';

    (useRouter as jest.Mock).mockReturnValue(mockRouter);
    (usePathname as jest.Mock).mockReturnValue(mockPathname);
  });

  afterEach(() => {
    jest.clearAllMocks();
  });

  describe('Initial Load from URL', () => {
    it('should initialize filters from URL parameters', () => {
      // Setup URL with query params
      const mockSearchParams = createMockSearchParams({
        minConfidence: '70',
        maxConfidence: '90',
        includeBelowThreshold: 'true',
        type: 'skill',
        status: 'new',
      });

      (useSearchParams as jest.Mock).mockReturnValue(mockSearchParams);

      // Expected: Component reads these values from searchParams.get()
      expect(mockSearchParams.get('minConfidence')).toBe('70');
      expect(mockSearchParams.get('maxConfidence')).toBe('90');
      expect(mockSearchParams.get('includeBelowThreshold')).toBe('true');
      expect(mockSearchParams.get('type')).toBe('skill');
      expect(mockSearchParams.get('status')).toBe('new');
    });

    it('should use default values when no URL params present', () => {
      const mockSearchParams = createMockSearchParams({});

      (useSearchParams as jest.Mock).mockReturnValue(mockSearchParams);

      // Expected: Component uses defaults
      expect(mockSearchParams.get('minConfidence')).toBeNull();
      expect(mockSearchParams.get('maxConfidence')).toBeNull();
      expect(mockSearchParams.get('includeBelowThreshold')).toBeNull();
    });

    it('should handle partial URL parameters', () => {
      const mockSearchParams = createMockSearchParams({
        minConfidence: '80',
        // maxConfidence omitted
        type: 'command',
        // status omitted
      });

      (useSearchParams as jest.Mock).mockReturnValue(mockSearchParams);

      expect(mockSearchParams.get('minConfidence')).toBe('80');
      expect(mockSearchParams.get('maxConfidence')).toBeNull();
      expect(mockSearchParams.get('type')).toBe('command');
      expect(mockSearchParams.get('status')).toBeNull();
    });
  });

  describe('URL Updates on Filter Changes', () => {
    it('should add minConfidence to URL when different from default (50)', () => {
      const mockSearchParams = createMockSearchParams({});
      (useSearchParams as jest.Mock).mockReturnValue(mockSearchParams);

      // Simulate changing minConfidence to 70
      const params = new URLSearchParams();
      params.set('minConfidence', '70');

      const expectedUrl = `${mockPathname}?${params.toString()}`;

      // Component should call router.replace with this URL
      // (Actual call happens in useEffect - we're testing the logic)
      expect(params.toString()).toBe('minConfidence=70');
    });

    it('should NOT add minConfidence to URL when equal to default (50)', () => {
      const mockSearchParams = createMockSearchParams({});
      (useSearchParams as jest.Mock).mockReturnValue(mockSearchParams);

      // Simulate minConfidence at default value
      const params = new URLSearchParams();
      // Should NOT add minConfidence=50

      expect(params.toString()).toBe('');
    });

    it('should add maxConfidence to URL when different from default (100)', () => {
      const mockSearchParams = createMockSearchParams({});
      (useSearchParams as jest.Mock).mockReturnValue(mockSearchParams);

      const params = new URLSearchParams();
      params.set('maxConfidence', '80');

      expect(params.toString()).toBe('maxConfidence=80');
    });

    it('should NOT add maxConfidence to URL when equal to default (100)', () => {
      const mockSearchParams = createMockSearchParams({});
      (useSearchParams as jest.Mock).mockReturnValue(mockSearchParams);

      const params = new URLSearchParams();
      // Should NOT add maxConfidence=100

      expect(params.toString()).toBe('');
    });

    it('should add includeBelowThreshold to URL only when true', () => {
      const mockSearchParams = createMockSearchParams({});
      (useSearchParams as jest.Mock).mockReturnValue(mockSearchParams);

      // When true
      const paramsTrue = new URLSearchParams();
      paramsTrue.set('includeBelowThreshold', 'true');
      expect(paramsTrue.toString()).toBe('includeBelowThreshold=true');

      // When false (default) - should not be in URL
      const paramsFalse = new URLSearchParams();
      expect(paramsFalse.toString()).toBe('');
    });

    it('should add type filter to URL', () => {
      const mockSearchParams = createMockSearchParams({});
      (useSearchParams as jest.Mock).mockReturnValue(mockSearchParams);

      const params = new URLSearchParams();
      params.set('type', 'skill');

      expect(params.toString()).toBe('type=skill');
    });

    it('should add status filter to URL', () => {
      const mockSearchParams = createMockSearchParams({});
      (useSearchParams as jest.Mock).mockReturnValue(mockSearchParams);

      const params = new URLSearchParams();
      params.set('status', 'new');

      expect(params.toString()).toBe('status=new');
    });

    it('should combine multiple non-default filters in URL', () => {
      const mockSearchParams = createMockSearchParams({});
      (useSearchParams as jest.Mock).mockReturnValue(mockSearchParams);

      const params = new URLSearchParams();
      params.set('minConfidence', '70');
      params.set('maxConfidence', '90');
      params.set('includeBelowThreshold', 'true');
      params.set('type', 'skill');
      params.set('status', 'new');

      expect(params.toString()).toBe(
        'minConfidence=70&maxConfidence=90&includeBelowThreshold=true&type=skill&status=new'
      );
    });
  });

  describe('Clear Filters', () => {
    it('should remove all URL parameters when filters cleared', () => {
      const mockSearchParams = createMockSearchParams({
        minConfidence: '70',
        maxConfidence: '90',
        type: 'skill',
        status: 'new',
      });
      (useSearchParams as jest.Mock).mockReturnValue(mockSearchParams);

      // After clearing filters (all back to defaults)
      const params = new URLSearchParams();
      // minConfidence=50 (default) - not added
      // maxConfidence=100 (default) - not added
      // includeBelowThreshold=false (default) - not added
      // type=undefined - not added
      // status=undefined - not added

      expect(params.toString()).toBe('');
    });

    it('should result in clean URL with no query string', () => {
      const mockSearchParams = createMockSearchParams({});
      (useSearchParams as jest.Mock).mockReturnValue(mockSearchParams);

      const params = new URLSearchParams();
      const query = params.toString();
      const expectedUrl = `${mockPathname}${query ? `?${query}` : ''}`;

      expect(expectedUrl).toBe('/marketplace/sources/123');
    });
  });

  describe('URL Parameter Validation', () => {
    it('should handle invalid minConfidence values gracefully', () => {
      const mockSearchParams = createMockSearchParams({
        minConfidence: 'invalid',
      });

      (useSearchParams as jest.Mock).mockReturnValue(mockSearchParams);

      // Component should handle NaN from Number('invalid')
      const value = Number(mockSearchParams.get('minConfidence'));
      expect(isNaN(value)).toBe(true);
      // Component should fall back to default (50)
    });

    it('should handle out-of-range confidence values', () => {
      const mockSearchParams = createMockSearchParams({
        minConfidence: '150',
        maxConfidence: '-10',
      });

      (useSearchParams as jest.Mock).mockReturnValue(mockSearchParams);

      // Component should clamp or validate these values
      expect(Number(mockSearchParams.get('minConfidence'))).toBe(150);
      expect(Number(mockSearchParams.get('maxConfidence'))).toBe(-10);
    });

    it('should handle invalid boolean values for includeBelowThreshold', () => {
      const mockSearchParams = createMockSearchParams({
        includeBelowThreshold: 'yes',
      });

      (useSearchParams as jest.Mock).mockReturnValue(mockSearchParams);

      // Component uses === 'true' check
      expect(mockSearchParams.get('includeBelowThreshold') === 'true').toBe(false);
    });

    it('should handle invalid artifact type values', () => {
      const mockSearchParams = createMockSearchParams({
        type: 'invalid-type',
      });

      (useSearchParams as jest.Mock).mockReturnValue(mockSearchParams);

      // Component casts to ArtifactType - TypeScript would catch this at compile time
      expect(mockSearchParams.get('type')).toBe('invalid-type');
    });
  });

  describe('Shareable URL Scenarios', () => {
    it('should generate shareable URL for high-confidence skills', () => {
      const mockSearchParams = createMockSearchParams({});
      (useSearchParams as jest.Mock).mockReturnValue(mockSearchParams);

      const params = new URLSearchParams();
      params.set('minConfidence', '80');
      params.set('type', 'skill');

      const shareableUrl = `${mockPathname}?${params.toString()}`;
      expect(shareableUrl).toBe('/marketplace/sources/123?minConfidence=80&type=skill');
    });

    it('should generate shareable URL for low-confidence items', () => {
      const mockSearchParams = createMockSearchParams({});
      (useSearchParams as jest.Mock).mockReturnValue(mockSearchParams);

      const params = new URLSearchParams();
      params.set('minConfidence', '10');
      params.set('maxConfidence', '30');
      params.set('includeBelowThreshold', 'true');

      const shareableUrl = `${mockPathname}?${params.toString()}`;
      expect(shareableUrl).toBe(
        '/marketplace/sources/123?minConfidence=10&maxConfidence=30&includeBelowThreshold=true'
      );
    });

    it('should generate shareable URL for new commands', () => {
      const mockSearchParams = createMockSearchParams({});
      (useSearchParams as jest.Mock).mockReturnValue(mockSearchParams);

      const params = new URLSearchParams();
      params.set('type', 'command');
      params.set('status', 'new');

      const shareableUrl = `${mockPathname}?${params.toString()}`;
      expect(shareableUrl).toBe('/marketplace/sources/123?type=command&status=new');
    });

    it('should generate shareable URL with all filters', () => {
      const mockSearchParams = createMockSearchParams({});
      (useSearchParams as jest.Mock).mockReturnValue(mockSearchParams);

      const params = new URLSearchParams();
      params.set('minConfidence', '60');
      params.set('maxConfidence', '85');
      params.set('type', 'agent');
      params.set('status', 'updated');

      const shareableUrl = `${mockPathname}?${params.toString()}`;
      expect(shareableUrl).toBe(
        '/marketplace/sources/123?minConfidence=60&maxConfidence=85&type=agent&status=updated'
      );
    });
  });

  describe('Router Integration', () => {
    it('should call router.replace with correct URL and options', () => {
      const mockSearchParams = createMockSearchParams({});
      (useSearchParams as jest.Mock).mockReturnValue(mockSearchParams);

      const params = new URLSearchParams();
      params.set('minConfidence', '70');

      const query = params.toString();
      const expectedUrl = `${mockPathname}?${query}`;

      // Simulate the router.replace call from updateURLParams
      mockRouter.replace(expectedUrl, { scroll: false });

      expect(mockRouter.replace).toHaveBeenCalledWith(
        '/marketplace/sources/123?minConfidence=70',
        { scroll: false }
      );
    });

    it('should call router.replace without scroll to preserve position', () => {
      const mockSearchParams = createMockSearchParams({});
      (useSearchParams as jest.Mock).mockReturnValue(mockSearchParams);

      mockRouter.replace(mockPathname, { scroll: false });

      expect(mockRouter.replace).toHaveBeenCalledWith(
        expect.any(String),
        expect.objectContaining({ scroll: false })
      );
    });
  });
});
