import type { AskResponse, Company, HealthResponse, ApiConfig } from '../types/api';

const DEFAULT_BASE_URL = import.meta.env.VITE_API_BASE_URL || '/api';
const DEFAULT_API_KEY = import.meta.env.VITE_API_KEY || 'SECTRA@Nitish';

export function getStoredConfig(): ApiConfig {
  const savedUrl = localStorage.getItem('sectra_api_base_url');
  const savedKey = localStorage.getItem('sectra_api_key');
  return {
    baseUrl: (savedUrl !== null ? savedUrl : DEFAULT_BASE_URL).replace(/\/+$/, ''),
    apiKey: savedKey !== null ? savedKey : DEFAULT_API_KEY,
  };
}

export function saveStoredConfig(config: ApiConfig): void {
  localStorage.setItem('sectra_api_base_url', config.baseUrl.replace(/\/+$/, ''));
  localStorage.setItem('sectra_api_key', config.apiKey);
}

export function resetStoredConfig(): ApiConfig {
  localStorage.removeItem('sectra_api_base_url');
  localStorage.removeItem('sectra_api_key');
  return {
    baseUrl: DEFAULT_BASE_URL.replace(/\/+$/, ''),
    apiKey: DEFAULT_API_KEY,
  };
}

async function request<T>(endpoint: string, options: RequestInit = {}): Promise<T> {
  const config = getStoredConfig();
  const url = `${config.baseUrl}${endpoint}`;

  const headers: Record<string, string> = {
    'Content-Type': 'application/json',
    ...(options.headers as Record<string, string>),
  };

  if (config.apiKey) {
    headers['X-API-Key'] = config.apiKey;
  }

  const response = await fetch(url, {
    ...options,
    headers,
  });

  if (!response.ok) {
    let errorDetail = response.statusText;
    try {
      const errorJson = await response.json();
      if (errorJson && errorJson.detail) {
        errorDetail = errorJson.detail;
      }
    } catch {
      // use default statusText
    }
    throw new Error(`API error (${response.status}): ${errorDetail}`);
  }

  return response.json();
}

export async function checkHealth(): Promise<{ data: HealthResponse; pingMs: number }> {
  const t0 = performance.now();
  const data = await request<HealthResponse>('/health');
  const pingMs = Math.round(performance.now() - t0);
  return { data, pingMs };
}

export async function fetchCompanies(): Promise<Company[]> {
  return request<Company[]>('/companies');
}

export async function submitQuestion(question: string): Promise<AskResponse> {
  return request<AskResponse>('/ask', {
    method: 'POST',
    body: JSON.stringify({ question: question.trim() }),
  });
}
