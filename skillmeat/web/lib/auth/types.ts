export interface AuthUser {
  id: string;
  email: string | null;
  name: string | null;
  imageUrl: string | null;
  /** Current active workspace/tenant */
  organizationId: string | null;
  organizations: Array<{ id: string; name: string; role: string }>;
}

export interface AuthProvider {
  /** Whether auth is enabled (false in local/noop mode) */
  isEnabled: boolean;
  /** Get current user (null if not signed in) */
  getUser(): AuthUser | null;
  /** Whether user is authenticated */
  isAuthenticated(): boolean;
  /** Get auth token for API calls */
  getToken(): Promise<string | null>;
  /** Sign out */
  signOut(): Promise<void>;
  /** Switch active organization/workspace */
  switchOrganization(orgId: string): Promise<void>;
}
