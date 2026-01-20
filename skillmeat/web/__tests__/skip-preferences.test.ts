/**
 * @jest-environment jsdom
 */
import {
  loadSkipPrefs,
  saveSkipPrefs,
  addSkipPref,
  removeSkipPref,
  clearSkipPrefs,
  isSkipped,
  buildArtifactKey,
} from '@/lib/skip-preferences';
import type { SkipPreference } from '@/types/discovery';

/**
 * Unit tests for LocalStorage skip preference utilities
 *
 * Tests the persistence layer for artifact skip preferences, including
 * CRUD operations, validation, edge cases, and graceful error handling.
 */
describe('skip-preferences', () => {
  const projectId = 'test-project-123';
  const storageKey = `skillmeat_skip_prefs_${projectId}`;

  beforeEach(() => {
    // Clear localStorage before each test
    localStorage.clear();
    jest.clearAllMocks();
  });

  afterEach(() => {
    // Cleanup after each test
    localStorage.clear();
  });

  describe('loadSkipPrefs', () => {
    it('returns empty array when no preferences exist', () => {
      const prefs = loadSkipPrefs(projectId);
      expect(prefs).toEqual([]);
      expect(Array.isArray(prefs)).toBe(true);
    });

    it('returns stored preferences', () => {
      const stored: SkipPreference[] = [
        {
          artifact_key: 'skill:test',
          skip_reason: 'Test reason',
          added_date: '2025-01-01T00:00:00Z',
        },
      ];
      localStorage.setItem(storageKey, JSON.stringify(stored));

      const prefs = loadSkipPrefs(projectId);
      expect(prefs).toEqual(stored);
      expect(prefs).toHaveLength(1);
      expect(prefs[0].artifact_key).toBe('skill:test');
    });

    it('returns multiple stored preferences', () => {
      const stored: SkipPreference[] = [
        {
          artifact_key: 'skill:canvas',
          skip_reason: 'Not needed',
          added_date: '2025-01-01T00:00:00Z',
        },
        {
          artifact_key: 'command:deploy',
          skip_reason: 'Already have custom version',
          added_date: '2025-01-02T00:00:00Z',
        },
      ];
      localStorage.setItem(storageKey, JSON.stringify(stored));

      const prefs = loadSkipPrefs(projectId);
      expect(prefs).toEqual(stored);
      expect(prefs).toHaveLength(2);
    });

    it('handles corrupted JSON gracefully', () => {
      localStorage.setItem(storageKey, 'invalid json {[}');
      const prefs = loadSkipPrefs(projectId);
      expect(prefs).toEqual([]);
    });

    it('handles null values gracefully', () => {
      localStorage.setItem(storageKey, 'null');
      const prefs = loadSkipPrefs(projectId);
      expect(prefs).toEqual([]);
    });

    it('handles undefined values gracefully', () => {
      localStorage.setItem(storageKey, 'undefined');
      const prefs = loadSkipPrefs(projectId);
      expect(prefs).toEqual([]);
    });

    it('handles different project IDs independently', () => {
      const project1Prefs: SkipPreference[] = [
        {
          artifact_key: 'skill:test1',
          skip_reason: 'Project 1',
          added_date: '2025-01-01T00:00:00Z',
        },
      ];
      const project2Prefs: SkipPreference[] = [
        {
          artifact_key: 'skill:test2',
          skip_reason: 'Project 2',
          added_date: '2025-01-02T00:00:00Z',
        },
      ];

      localStorage.setItem(`skillmeat_skip_prefs_project1`, JSON.stringify(project1Prefs));
      localStorage.setItem(`skillmeat_skip_prefs_project2`, JSON.stringify(project2Prefs));

      const prefs1 = loadSkipPrefs('project1');
      const prefs2 = loadSkipPrefs('project2');

      expect(prefs1).toEqual(project1Prefs);
      expect(prefs2).toEqual(project2Prefs);
      expect(prefs1[0].artifact_key).not.toBe(prefs2[0].artifact_key);
    });

    it('returns empty array when localStorage is unavailable', () => {
      // Mock localStorage to throw
      const originalGetItem = Storage.prototype.getItem;
      Storage.prototype.getItem = jest.fn(() => {
        throw new Error('Storage unavailable');
      });

      const prefs = loadSkipPrefs(projectId);
      expect(prefs).toEqual([]);

      // Restore
      Storage.prototype.getItem = originalGetItem;
    });
  });

  describe('saveSkipPrefs', () => {
    it('saves preferences to localStorage', () => {
      const prefs: SkipPreference[] = [
        {
          artifact_key: 'skill:test',
          skip_reason: 'Test',
          added_date: '2025-01-01T00:00:00Z',
        },
      ];
      saveSkipPrefs(projectId, prefs);

      const stored = localStorage.getItem(storageKey);
      expect(stored).not.toBeNull();
      expect(JSON.parse(stored!)).toEqual(prefs);
    });

    it('overwrites existing preferences', () => {
      const prefs1: SkipPreference[] = [
        { artifact_key: 'skill:old', skip_reason: 'Old', added_date: '2025-01-01T00:00:00Z' },
      ];
      const prefs2: SkipPreference[] = [
        { artifact_key: 'skill:new', skip_reason: 'New', added_date: '2025-01-02T00:00:00Z' },
      ];

      saveSkipPrefs(projectId, prefs1);
      saveSkipPrefs(projectId, prefs2);

      const stored = localStorage.getItem(storageKey);
      expect(JSON.parse(stored!)).toEqual(prefs2);
      expect(JSON.parse(stored!)).not.toEqual(prefs1);
    });

    it('handles empty array', () => {
      saveSkipPrefs(projectId, []);

      const stored = localStorage.getItem(storageKey);
      expect(stored).not.toBeNull();
      expect(JSON.parse(stored!)).toEqual([]);
    });

    it('handles localStorage quota exceeded gracefully', () => {
      // Mock localStorage to throw quota exceeded error
      const originalSetItem = Storage.prototype.setItem;
      Storage.prototype.setItem = jest.fn(() => {
        throw new DOMException('QuotaExceededError');
      });

      const prefs: SkipPreference[] = [
        { artifact_key: 'skill:test', skip_reason: 'Test', added_date: '2025-01-01T00:00:00Z' },
      ];

      // Should not throw
      expect(() => saveSkipPrefs(projectId, prefs)).not.toThrow();

      // Restore
      Storage.prototype.setItem = originalSetItem;
    });
  });

  describe('addSkipPref', () => {
    it('adds new preference', () => {
      const pref = addSkipPref(projectId, 'skill:canvas', 'Not needed for this project');

      expect(pref.artifact_key).toBe('skill:canvas');
      expect(pref.skip_reason).toBe('Not needed for this project');
      expect(pref.added_date).toBeTruthy();
      expect(new Date(pref.added_date).toString()).not.toBe('Invalid Date');
    });

    it('persists preference to localStorage', () => {
      addSkipPref(projectId, 'skill:canvas', 'Test reason');

      const stored = loadSkipPrefs(projectId);
      expect(stored).toHaveLength(1);
      expect(stored[0].artifact_key).toBe('skill:canvas');
    });

    it('adds preference marked as skipped via isSkipped', () => {
      expect(isSkipped(projectId, 'skill:canvas')).toBe(false);

      addSkipPref(projectId, 'skill:canvas', 'Test');

      expect(isSkipped(projectId, 'skill:canvas')).toBe(true);
    });

    it('prevents duplicate preferences', () => {
      addSkipPref(projectId, 'skill:canvas', 'First reason');
      addSkipPref(projectId, 'skill:canvas', 'Second reason');

      const prefs = loadSkipPrefs(projectId);
      expect(prefs).toHaveLength(1);
      expect(prefs[0].skip_reason).toBe('First reason'); // First one kept
    });

    it('allows multiple different artifacts', () => {
      addSkipPref(projectId, 'skill:canvas', 'Reason 1');
      addSkipPref(projectId, 'command:deploy', 'Reason 2');

      const prefs = loadSkipPrefs(projectId);
      expect(prefs).toHaveLength(2);
      expect(prefs.map((p) => p.artifact_key)).toContain('skill:canvas');
      expect(prefs.map((p) => p.artifact_key)).toContain('command:deploy');
    });

    it('adds preference with ISO 8601 timestamp', () => {
      const beforeAdd = new Date().toISOString();
      const pref = addSkipPref(projectId, 'skill:test', 'Test');
      const afterAdd = new Date().toISOString();

      expect(pref.added_date).toMatch(/^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}\.\d{3}Z$/);
      expect(pref.added_date >= beforeAdd).toBe(true);
      expect(pref.added_date <= afterAdd).toBe(true);
    });

    it('handles empty reason string', () => {
      const pref = addSkipPref(projectId, 'skill:test', '');

      expect(pref.skip_reason).toBe('');
      expect(isSkipped(projectId, 'skill:test')).toBe(true);
    });
  });

  describe('removeSkipPref', () => {
    it('removes existing preference', () => {
      addSkipPref(projectId, 'skill:test', 'Test');
      expect(isSkipped(projectId, 'skill:test')).toBe(true);

      const result = removeSkipPref(projectId, 'skill:test');

      expect(result).toBe(true);
      expect(isSkipped(projectId, 'skill:test')).toBe(false);
    });

    it('removes correct preference from multiple', () => {
      addSkipPref(projectId, 'skill:canvas', 'Test 1');
      addSkipPref(projectId, 'skill:deploy', 'Test 2');
      addSkipPref(projectId, 'command:test', 'Test 3');

      const result = removeSkipPref(projectId, 'skill:deploy');

      expect(result).toBe(true);
      const prefs = loadSkipPrefs(projectId);
      expect(prefs).toHaveLength(2);
      expect(prefs.map((p) => p.artifact_key)).toContain('skill:canvas');
      expect(prefs.map((p) => p.artifact_key)).toContain('command:test');
      expect(prefs.map((p) => p.artifact_key)).not.toContain('skill:deploy');
    });

    it('returns false when preference not found', () => {
      const result = removeSkipPref(projectId, 'skill:nonexistent');
      expect(result).toBe(false);
    });

    it('returns false when removing from empty list', () => {
      expect(loadSkipPrefs(projectId)).toHaveLength(0);
      const result = removeSkipPref(projectId, 'skill:test');
      expect(result).toBe(false);
    });

    it('persists removal to localStorage', () => {
      addSkipPref(projectId, 'skill:test', 'Test');
      removeSkipPref(projectId, 'skill:test');

      const stored = localStorage.getItem(storageKey);
      expect(stored).not.toBeNull();
      expect(JSON.parse(stored!)).toEqual([]);
    });
  });

  describe('clearSkipPrefs', () => {
    it('removes all preferences', () => {
      addSkipPref(projectId, 'skill:one', 'One');
      addSkipPref(projectId, 'skill:two', 'Two');
      addSkipPref(projectId, 'command:three', 'Three');

      expect(loadSkipPrefs(projectId)).toHaveLength(3);

      clearSkipPrefs(projectId);

      expect(loadSkipPrefs(projectId)).toEqual([]);
    });

    it('removes localStorage entry completely', () => {
      addSkipPref(projectId, 'skill:test', 'Test');
      expect(localStorage.getItem(storageKey)).not.toBeNull();

      clearSkipPrefs(projectId);

      expect(localStorage.getItem(storageKey)).toBeNull();
    });

    it('handles clearing empty preferences', () => {
      expect(loadSkipPrefs(projectId)).toHaveLength(0);

      // Should not throw
      expect(() => clearSkipPrefs(projectId)).not.toThrow();

      expect(localStorage.getItem(storageKey)).toBeNull();
    });

    it('does not affect other projects', () => {
      addSkipPref('project1', 'skill:test1', 'Test 1');
      addSkipPref('project2', 'skill:test2', 'Test 2');

      clearSkipPrefs('project1');

      expect(loadSkipPrefs('project1')).toHaveLength(0);
      expect(loadSkipPrefs('project2')).toHaveLength(1);
    });

    it('handles localStorage unavailability gracefully', () => {
      // Mock localStorage to throw
      const originalRemoveItem = Storage.prototype.removeItem;
      Storage.prototype.removeItem = jest.fn(() => {
        throw new Error('Storage unavailable');
      });

      // Should not throw
      expect(() => clearSkipPrefs(projectId)).not.toThrow();

      // Restore
      Storage.prototype.removeItem = originalRemoveItem;
    });
  });

  describe('isSkipped', () => {
    it('returns true for skipped artifacts', () => {
      addSkipPref(projectId, 'skill:skipped', 'Skipped');
      expect(isSkipped(projectId, 'skill:skipped')).toBe(true);
    });

    it('returns false for non-skipped artifacts', () => {
      expect(isSkipped(projectId, 'skill:not-skipped')).toBe(false);
    });

    it('returns false for empty preferences', () => {
      expect(loadSkipPrefs(projectId)).toHaveLength(0);
      expect(isSkipped(projectId, 'skill:any')).toBe(false);
    });

    it('checks exact artifact key match', () => {
      addSkipPref(projectId, 'skill:canvas', 'Test');

      expect(isSkipped(projectId, 'skill:canvas')).toBe(true);
      expect(isSkipped(projectId, 'skill:canvas2')).toBe(false);
      expect(isSkipped(projectId, 'command:canvas')).toBe(false);
    });

    it('handles case-sensitive keys', () => {
      addSkipPref(projectId, 'skill:Canvas', 'Test');

      expect(isSkipped(projectId, 'skill:Canvas')).toBe(true);
      expect(isSkipped(projectId, 'skill:canvas')).toBe(false);
      expect(isSkipped(projectId, 'skill:CANVAS')).toBe(false);
    });

    it('works correctly after removal', () => {
      addSkipPref(projectId, 'skill:test', 'Test');
      expect(isSkipped(projectId, 'skill:test')).toBe(true);

      removeSkipPref(projectId, 'skill:test');
      expect(isSkipped(projectId, 'skill:test')).toBe(false);
    });
  });

  describe('buildArtifactKey', () => {
    it('builds correct format for skill', () => {
      expect(buildArtifactKey('skill', 'canvas')).toBe('skill:canvas');
    });

    it('builds correct format for command', () => {
      expect(buildArtifactKey('command', 'deploy')).toBe('command:deploy');
    });

    it('builds correct format for agent', () => {
      expect(buildArtifactKey('agent', 'my-agent')).toBe('agent:my-agent');
    });

    it('handles names with hyphens', () => {
      expect(buildArtifactKey('skill', 'canvas-design')).toBe('skill:canvas-design');
    });

    it('handles names with underscores', () => {
      expect(buildArtifactKey('command', 'my_command')).toBe('command:my_command');
    });

    it('handles empty strings', () => {
      expect(buildArtifactKey('', '')).toBe(':');
      expect(buildArtifactKey('skill', '')).toBe('skill:');
      expect(buildArtifactKey('', 'test')).toBe(':test');
    });

    it('handles special characters', () => {
      expect(buildArtifactKey('skill', 'test@1.0')).toBe('skill:test@1.0');
      expect(buildArtifactKey('skill', 'test/path')).toBe('skill:test/path');
    });
  });

  describe('Edge Cases & Integration', () => {
    it('handles rapid add/remove operations', () => {
      const artifactKey = 'skill:test';

      for (let i = 0; i < 10; i++) {
        addSkipPref(projectId, artifactKey, `Reason ${i}`);
        removeSkipPref(projectId, artifactKey);
      }

      expect(isSkipped(projectId, artifactKey)).toBe(false);
    });

    it('handles large number of preferences', () => {
      const count = 100;

      for (let i = 0; i < count; i++) {
        addSkipPref(projectId, `skill:test${i}`, `Reason ${i}`);
      }

      const prefs = loadSkipPrefs(projectId);
      expect(prefs).toHaveLength(count);

      // Verify random entries
      expect(isSkipped(projectId, 'skill:test0')).toBe(true);
      expect(isSkipped(projectId, 'skill:test50')).toBe(true);
      expect(isSkipped(projectId, 'skill:test99')).toBe(true);
    });

    it('preserves preference data integrity through save/load cycle', () => {
      const originalPrefs: SkipPreference[] = [
        {
          artifact_key: 'skill:canvas',
          skip_reason: 'Not needed for this project',
          added_date: '2025-01-01T12:34:56.789Z',
        },
        {
          artifact_key: 'command:deploy',
          skip_reason: 'Using custom deployment',
          added_date: '2025-01-02T09:15:30.123Z',
        },
      ];

      saveSkipPrefs(projectId, originalPrefs);
      const loadedPrefs = loadSkipPrefs(projectId);

      expect(loadedPrefs).toEqual(originalPrefs);
      expect(loadedPrefs[0]).toMatchObject(originalPrefs[0]);
      expect(loadedPrefs[1]).toMatchObject(originalPrefs[1]);
    });

    it('handles concurrent access from different projects', () => {
      const project1 = 'project-1';
      const project2 = 'project-2';

      addSkipPref(project1, 'skill:test1', 'Project 1');
      addSkipPref(project2, 'skill:test2', 'Project 2');

      expect(isSkipped(project1, 'skill:test1')).toBe(true);
      expect(isSkipped(project1, 'skill:test2')).toBe(false);
      expect(isSkipped(project2, 'skill:test1')).toBe(false);
      expect(isSkipped(project2, 'skill:test2')).toBe(true);
    });

    it('handles unicode characters in artifact names', () => {
      const unicodeName = 'skill:测试-test-тест';
      addSkipPref(projectId, unicodeName, 'Unicode test');

      expect(isSkipped(projectId, unicodeName)).toBe(true);

      const prefs = loadSkipPrefs(projectId);
      expect(prefs[0].artifact_key).toBe(unicodeName);
    });
  });
});
