export interface TableData {
  sql: string;
  columns: string[];
  rows: (string | number | null)[][];
  source_filings: string[];
}

export interface Passage {
  n: number;
  cited: boolean;
  header: string;
  text: string;
  score: number;
  chunk_id: string;
  ticker?: string | null;
  fiscal_year?: number | null;
  item_code?: string | null;
  url?: string | null;
}

export interface AskWarnings {
  uncited_sentences?: string[];
  unsupported_numbers?: (string | number)[];
  invalid_citations?: string[];
  truncated?: boolean;
  [key: string]: unknown;
}

export interface AskResponse {
  question: string;
  answer: string;
  route: 'sql' | 'text' | 'both' | 'none' | string;
  answered: boolean;
  reason: string;
  tickers: string[];
  fiscal_years: number[];
  table?: TableData | null;
  passages: Passage[];
  warnings: AskWarnings;
  steps: string[];
  model: string;
  input_tokens: number;
  output_tokens: number;
  latency_ms: number;
}

export interface Company {
  ticker: string;
  name: string;
  sector: string;
  text_years: number[];
  metric_years: number[];
}

export interface HealthResponse {
  status: string;
  companies: number;
  metrics: number;
  llm: string | null;
}

export interface ApiConfig {
  baseUrl: string;
  apiKey: string;
}
