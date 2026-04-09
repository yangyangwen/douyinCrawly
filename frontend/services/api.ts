/**
 * Shared HTTP API client.
 */

import { AppSettings, DouyinWork, TaskType } from '../types';

declare global {
  interface Window {
    __DOUYIN_API_AUTH_TOKEN__?: string;
  }
}

function resolveApiBaseUrl(): string {
  const configuredBaseUrl = import.meta.env.VITE_API_BASE_URL?.trim();
  if (configuredBaseUrl) {
    return configuredBaseUrl.replace(/\/$/, '');
  }

  if (typeof window !== 'undefined' && window.location.origin && window.location.protocol !== 'file:') {
    return window.location.origin.replace(/\/$/, '');
  }

  return 'http://127.0.0.1:8000';
}

function resolveApiAuthToken(): string {
  const configuredToken = import.meta.env.VITE_API_AUTH_TOKEN?.trim();
  if (configuredToken) {
    return configuredToken;
  }

  if (typeof window === 'undefined') {
    return '';
  }

  const runtimeToken = window.__DOUYIN_API_AUTH_TOKEN__?.trim();
  if (runtimeToken) {
    return runtimeToken;
  }

  try {
    const storedToken = window.localStorage.getItem('DOUYIN_API_AUTH_TOKEN')?.trim();
    if (storedToken) {
      return storedToken;
    }
  } catch {
    // Ignore localStorage access errors.
  }

  return '';
}

export const API_BASE_URL = resolveApiBaseUrl();

export class APIError extends Error {
  constructor(
    public statusCode: number,
    public detail: string,
    public code?: string,
    public details?: unknown,
  ) {
    super(detail);
    this.name = 'APIError';
  }
}

export interface StartTaskParams {
  type: TaskType | string;
  target: string;
  limit?: number;
  filters?: Record<string, string>;
}

export interface TaskResponse {
  task_id: string;
  status: string;
}

export interface TaskStatus {
  id: string;
  type: string;
  target: string;
  status: 'running' | 'completed' | 'error';
  progress: number;
  result_count: number;
  error?: string;
  created_at: number;
  updated_at: number;
  aria2_conf?: string;
}

export interface HealthStatus {
  ready: boolean;
  aria2: boolean;
  config: boolean;
  error?: string;
}

export interface Aria2Config {
  host: string;
  port: number;
  secret: string;
}

interface HeaderOptions {
  includeJsonContentType?: boolean;
}

function parseAPIError(
  statusCode: number,
  fallbackMessage: string,
  errorData: unknown,
): APIError {
  if (errorData && typeof errorData === 'object') {
    const data = errorData as {
      error?: {
        code?: string;
        message?: string;
        details?: unknown;
      };
      detail?: string | { message?: string };
    };

    if (data.error) {
      return new APIError(
        statusCode,
        data.error.message || fallbackMessage,
        data.error.code,
        data.error.details,
      );
    }

    if (typeof data.detail === 'string') {
      return new APIError(statusCode, data.detail);
    }

    if (data.detail && typeof data.detail === 'object' && 'message' in data.detail) {
      const detail = data.detail as { message?: string };
      return new APIError(statusCode, detail.message || fallbackMessage);
    }
  }

  return new APIError(statusCode, fallbackMessage);
}

export function getApiAuthToken(): string {
  return resolveApiAuthToken();
}

export function buildApiUrl(endpoint: string): string {
  return `${API_BASE_URL}${endpoint}`;
}

export function buildRequestHeaders(
  headers?: HeadersInit,
  options: HeaderOptions = {},
): Headers {
  const resolvedHeaders = new Headers(headers);

  if (options.includeJsonContentType !== false && !resolvedHeaders.has('Content-Type')) {
    resolvedHeaders.set('Content-Type', 'application/json');
  }

  const token = getApiAuthToken();
  if (token && !resolvedHeaders.has('Authorization')) {
    resolvedHeaders.set('Authorization', `Bearer ${token}`);
  }

  return resolvedHeaders;
}

export function buildAuthenticatedUrl(endpoint: string): string {
  const url = new URL(buildApiUrl(endpoint));
  const token = getApiAuthToken();
  if (token) {
    url.searchParams.set('api_token', token);
  }
  return url.toString();
}

async function fetchAPI<T>(
  endpoint: string,
  options: RequestInit = {},
): Promise<T> {
  const response = await fetch(buildApiUrl(endpoint), {
    ...options,
    headers: buildRequestHeaders(options.headers),
  });

  if (!response.ok) {
    const fallbackMessage = response.statusText || `HTTP ${response.status}`;
    const errorData = await response.json().catch(() => null);
    throw parseAPIError(response.status, fallbackMessage, errorData);
  }

  return response.json();
}

async function get<T>(endpoint: string): Promise<T> {
  return fetchAPI<T>(endpoint, { method: 'GET' });
}

async function post<T>(endpoint: string, body?: unknown): Promise<T> {
  return fetchAPI<T>(endpoint, {
    method: 'POST',
    body: body ? JSON.stringify(body) : undefined,
  });
}

export const api = {
  baseUrl: API_BASE_URL,

  health: () => get<HealthStatus>('/api/health'),

  isAvailable: async (): Promise<boolean> => {
    try {
      const response = await fetch(buildApiUrl('/api'), {
        method: 'GET',
        headers: buildRequestHeaders(undefined, { includeJsonContentType: false }),
        signal: AbortSignal.timeout(2000),
      });
      return response.ok;
    } catch {
      return false;
    }
  },

  waitForReady: async (timeout = 30000): Promise<boolean> => {
    const startTime = Date.now();
    const checkInterval = 500;

    while (Date.now() - startTime < timeout) {
      if (await api.isAvailable()) {
        console.log(`[API] backend ready (${Date.now() - startTime}ms)`);
        return true;
      }
      await new Promise(resolve => setTimeout(resolve, checkInterval));
    }

    console.error('[API] connection timeout');
    return false;
  },

  settings: {
    get: () => get<AppSettings>('/api/settings'),
    save: (data: Partial<AppSettings>) =>
      post<{ status: string; message: string }>('/api/settings', data),
    isFirstRun: async () => {
      const result = await get<{ is_first_run: boolean }>('/api/settings/first-run');
      return result.is_first_run;
    },
  },

  task: {
    start: (params: StartTaskParams) =>
      post<TaskResponse>('/api/task/start', {
        type: params.type,
        target: params.target,
        limit: params.limit ?? 0,
        filters: params.filters ?? null,
      }),
    status: (taskId?: string) => {
      const query = taskId ? `?task_id=${encodeURIComponent(taskId)}` : '';
      return get<TaskStatus[]>(`/api/task/status${query}`);
    },
    results: (taskId: string) =>
      get<DouyinWork[]>(`/api/task/results/${encodeURIComponent(taskId)}`),
  },

  aria2: {
    config: () => get<Aria2Config>('/api/aria2/config'),
    status: async () => {
      const result = await get<{ connected: boolean }>('/api/aria2/status');
      return result.connected;
    },
    start: () => post<{ status: string; message: string }>('/api/aria2/start'),
    configPath: async (taskId?: string) => {
      const query = taskId ? `?task_id=${encodeURIComponent(taskId)}` : '';
      const result = await get<{ config_path: string }>(`/api/aria2/config-path${query}`);
      return result.config_path;
    },
  },

  file: {
    openFolder: async (path: string) => {
      const result = await post<{ success: boolean }>('/api/file/open-folder', { folder_path: path });
      return result.success;
    },
    checkExists: async (path: string) => {
      const result = await post<{ exists: boolean }>('/api/file/check-exists', { file_path: path });
      return result.exists;
    },
    readConfig: async (path: string) => {
      const result = await post<{ content: string }>('/api/file/read-config', { file_path: path });
      return result.content;
    },
    findLocal: (workId: string) =>
      get<{ found: boolean; video_path: string | null; images: string[] | null }>(
        `/api/file/find-local/${encodeURIComponent(workId)}`,
      ),
    getMediaUrl: (filePath: string) => {
      const encodedPath = filePath
        .split(/[/\\]/)
        .map(segment => encodeURIComponent(segment))
        .join('/');
      return buildAuthenticatedUrl(`/api/file/media/${encodedPath}`);
    },
  },

  system: {
    clipboard: async () => {
      const result = await get<{ text: string }>('/api/system/clipboard');
      return result.text;
    },
    openUrl: (url: string) =>
      post<{ status: string; message: string }>('/api/system/open-url', { url }),
    cookieLogin: () =>
      post<{ success: boolean; cookie: string; user_agent: string; error: string }>(
        '/api/system/cookie-login',
      ),
  },
};

export default api;
