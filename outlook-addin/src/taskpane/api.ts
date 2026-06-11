// ---------------------------------------------------------------------------
// Backend API client for MailPilot
// ---------------------------------------------------------------------------

/** Base URL of the FastAPI backend. Override via env var at build time. */
export const BACKEND_URL: string =
  (import.meta as Record<string, any>).env?.VITE_BACKEND_URL ?? "http://localhost:8000";

/** API key sent with every request. In production, retrieve from a secure store. */
export const API_TOKEN: string =
  (import.meta as Record<string, any>).env?.VITE_API_TOKEN ?? "dev-token";

// ---- Request / Response interfaces ----------------------------------------
// These must match the backend Pydantic schemas exactly.

export interface EmailContact {
  name: string | null;
  email: string | null;
}

export interface UserContext {
  preferred_categories?: string[];
  timezone?: string;
}

export interface EmailAnalysisRequest {
  provider: string;
  message_id: string;
  conversation_id?: string | null;
  subject: string;
  sender: EmailContact;
  to?: EmailContact[];
  cc?: EmailContact[];
  received_at: string;
  body_text: string;
  existing_categories?: string[];
  user_context?: UserContext | null;
}

export interface CategoryRecommendation {
  name: string;
  confidence: number;
  reason: string;
}

export interface Deadline {
  exists: boolean;
  date: string | null;
  evidence: string | null;
}

export interface CacheInfo {
  hit: boolean;
  content_hash: string;
}

export interface EmailAnalysisResponse {
  message_id: string;
  summary: string;
  priority: "high" | "medium" | "low";
  recommended_categories: CategoryRecommendation[];
  suggested_action: string;
  needs_reply: boolean;
  deadline: Deadline;
  cache: CacheInfo;
}

export interface CategoryListResponse {
  taxonomy_version: string;
  categories: string[];
}

export interface HealthResponse {
  status: string;
  version: string;
}

// ---- Shared fetch helper --------------------------------------------------

async function apiFetch<T>(path: string, options: RequestInit = {}): Promise<T> {
  const url = `${BACKEND_URL}${path}`;
  const res = await fetch(url, {
    ...options,
    headers: {
      "Content-Type": "application/json",
      "X-API-Key": API_TOKEN,
      ...(options.headers as Record<string, string> | undefined),
    },
  });

  if (!res.ok) {
    const detail = await res.text().catch(() => "Unknown error");
    throw new Error(`API ${res.status}: ${detail}`);
  }

  return res.json() as Promise<T>;
}

// ---- Public API functions -------------------------------------------------

/** Send an email to the backend for summarization and categorization. */
export async function analyzeEmail(
  request: EmailAnalysisRequest,
): Promise<EmailAnalysisResponse> {
  return apiFetch<EmailAnalysisResponse>("/api/email/analyze", {
    method: "POST",
    body: JSON.stringify(request),
  });
}

/** Retrieve the full list of available categories from the backend. */
export async function getCategories(): Promise<CategoryListResponse> {
  return apiFetch<CategoryListResponse>("/api/categories");
}

/** Health-check ping. */
export async function checkHealth(): Promise<HealthResponse> {
  return apiFetch<HealthResponse>("/api/health");
}
