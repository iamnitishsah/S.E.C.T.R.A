import type { AskResponse, Company, HealthResponse } from '../types/api';

// The API Base URL is strictly controlled by environment configuration (e.g. Vercel env or .env)
export const API_BASE_URL = (import.meta.env.VITE_API_BASE_URL || 'http://32.236.49.234:8000').replace(/\/+$/, '');
const DEFAULT_API_KEY = import.meta.env.VITE_API_KEY || 'SECTRA@Nitish';

export function getStoredApiKey(): string {
  const savedKey = localStorage.getItem('sectra_api_key');
  return savedKey !== null ? savedKey : DEFAULT_API_KEY;
}

export function saveStoredApiKey(apiKey: string): void {
  localStorage.setItem('sectra_api_key', apiKey.trim());
}

export function resetStoredApiKey(): string {
  localStorage.removeItem('sectra_api_key');
  return DEFAULT_API_KEY;
}

async function request<T>(endpoint: string, options: RequestInit = {}): Promise<T> {
  const apiKey = getStoredApiKey();
  const url = `${API_BASE_URL}${endpoint}`;

  const headers: Record<string, string> = {
    'Content-Type': 'application/json',
    ...(options.headers as Record<string, string>),
  };

  if (apiKey) {
    headers['X-API-Key'] = apiKey;
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
