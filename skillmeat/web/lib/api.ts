const API_BASE_URL = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8080";
const API_VERSION = process.env.NEXT_PUBLIC_API_VERSION || "v1";
const API_KEY = process.env.NEXT_PUBLIC_API_KEY;
const API_TOKEN = process.env.NEXT_PUBLIC_API_TOKEN;

export const apiConfig = {
  baseUrl: API_BASE_URL,
  version: API_VERSION,
  apiKey: API_KEY,
  apiToken: API_TOKEN,
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
  const normalizedPath = path.startsWith("/") ? path : `/${path}`;
  return `${API_BASE_URL}/api/${API_VERSION}${normalizedPath}`;
}

export function buildApiHeaders(extra?: HeadersInit): HeadersInit {
  const headers: Record<string, string> = { Accept: "application/json" };

  const extraEntries =
    extra instanceof Headers
      ? Object.fromEntries(extra.entries())
      : (extra as Record<string, string> | undefined);

  if (API_TOKEN) {
    headers["Authorization"] = `Bearer ${API_TOKEN}`;
  }

  if (API_KEY) {
    headers["X-API-Key"] = API_KEY;
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

  const response = await fetch(buildApiUrl(path), requestInit);
  const contentType = response.headers.get("content-type");
  const isJson = contentType?.includes("application/json");
  const body = isJson ? await response.json() : undefined;

  if (!response.ok) {
    throw new ApiError("Request failed", response.status, body);
  }

  return body as T;
}
