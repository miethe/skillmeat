const API_BASE_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8080';
const API_VERSION = process.env.NEXT_PUBLIC_API_VERSION || 'v1';
const API_KEY = process.env.NEXT_PUBLIC_API_KEY;
const API_TOKEN = process.env.NEXT_PUBLIC_API_TOKEN;
const ENABLE_API_MOCKS = process.env.NEXT_PUBLIC_ENABLE_API_MOCKS === 'true';
const ENABLE_API_TRACE = process.env.NEXT_PUBLIC_API_TRACE === 'true';

export const apiConfig = {
  baseUrl: API_BASE_URL,
  version: API_VERSION,
  apiKey: API_KEY,
  apiToken: API_TOKEN,
  useMocks: ENABLE_API_MOCKS,
  trace: ENABLE_API_TRACE,
};

export class ApiError extends Error {
  status: number;
  body?: unknown;

  constructor(message: string, status: number, body?: unknown) {
    super(message);
    this.status = status;
    this.body = body;
  }
}

function buildApiUrl(path: string) {
  const normalizedPath = path.startsWith('/') ? path : `/${path}`;
  return `${API_BASE_URL}/api/${API_VERSION}${normalizedPath}`;
}

function trace(event: string, detail: Record<string, unknown>) {
  if (!ENABLE_API_TRACE) return;
  const timestamp = new Date().toISOString();
  // Console-only tracing to avoid external dependencies
  // eslint-disable-next-line no-console
  console.info(`[api-trace] ${timestamp} ${event}`, detail);
}

export function buildApiHeaders(extra?: HeadersInit): HeadersInit {
  const headers: Record<string, string> = {
    Accept: 'application/json',
    'Content-Type': 'application/json',
  };

  const extraEntries =
    extra instanceof Headers
      ? Object.fromEntries(extra.entries())
      : (extra as Record<string, string> | undefined);

  if (API_TOKEN) {
    headers['Authorization'] = `Bearer ${API_TOKEN}`;
  }

  if (API_KEY) {
    headers['X-API-Key'] = API_KEY;
  }

  return {
    ...headers,
    ...extraEntries,
  };
}

export async function apiRequest<T>(path: string, init?: RequestInit): Promise<T> {
  const requestInit: RequestInit = {
    ...init,
    headers: buildApiHeaders(init?.headers),
  };

  const url = buildApiUrl(path);
  trace('request:start', { url, method: requestInit.method || 'GET' });

  const response = await fetch(url, requestInit);

  // Handle 204 No Content - return undefined (cast to T for void returns)
  if (response.status === 204) {
    trace('request:success', { url, status: response.status });
    return undefined as T;
  }

  const contentType = response.headers.get('content-type');
  const isJson = contentType?.includes('application/json');
  const body = isJson ? await response.json() : undefined;

  if (!response.ok) {
    trace('request:error', {
      url,
      status: response.status,
      statusText: response.statusText,
      body,
    });
    throw new ApiError('Request failed', response.status, body);
  }

  trace('request:success', { url, status: response.status });
  return body as T;
}

export interface ApiResponseWithHeaders<T> {
  data: T;
  headers: Headers;
}

/**
 * Like `apiRequest`, but also returns the raw response Headers object.
 *
 * Use this when callers need to inspect response headers (e.g., X-Cache,
 * X-Cache-Age, X-RateLimit-*). For standard requests that only need the
 * response body, prefer `apiRequest`.
 */
export async function apiRequestWithHeaders<T>(
  path: string,
  init?: RequestInit
): Promise<ApiResponseWithHeaders<T>> {
  const requestInit: RequestInit = {
    ...init,
    headers: buildApiHeaders(init?.headers),
  };

  const url = buildApiUrl(path);
  trace('request:start', { url, method: requestInit.method || 'GET' });

  const response = await fetch(url, requestInit);

  // Handle 204 No Content
  if (response.status === 204) {
    trace('request:success', { url, status: response.status });
    return { data: undefined as T, headers: response.headers };
  }

  const contentType = response.headers.get('content-type');
  const isJson = contentType?.includes('application/json');
  const body = isJson ? await response.json() : undefined;

  if (!response.ok) {
    trace('request:error', {
      url,
      status: response.status,
      statusText: response.statusText,
      body,
    });
    throw new ApiError('Request failed', response.status, body);
  }

  trace('request:success', { url, status: response.status });
  return { data: body as T, headers: response.headers };
}
