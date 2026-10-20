export const API_URL = import.meta.env.VITE_API_URL ?? "http://localhost:8000";
const SESSION_KEY = "learn-english-session";
export const AUTH_CHANGED = "learn-english-auth-changed";

export function sessionToken() {
  return sessionStorage.getItem(SESSION_KEY);
}

export function setSessionToken(token: string | null) {
  if (token) sessionStorage.setItem(SESSION_KEY, token);
  else sessionStorage.removeItem(SESSION_KEY);
  window.dispatchEvent(new Event(AUTH_CHANGED));
}

export async function apiFetch(input: string, init?: RequestInit) {
  const token = sessionToken();
  const headers = new Headers(init?.headers);
  if (token) headers.set("Authorization", `Bearer ${token}`);
  const response = await fetch(input, { ...init, headers });
  if (response.status === 401 && token === sessionToken()) setSessionToken(null);
  return response;
}

export class ApiError extends Error {
  retryAfter: number;
  constructor(message: string, retryAfter = 0) {
    super(message);
    this.retryAfter = retryAfter;
  }
}

export async function dictionaryRequest(path: "lookup" | "audio", term: string, signal: AbortSignal) {
  const response = await apiFetch(`${API_URL}/dictionary/${path}`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ term }),
    signal,
  });
  if (!response.ok) {
    const data = await response.json().catch(() => null);
    const detail = typeof data?.detail === "string" ? data.detail :
      response.status === 422 ? "Chỉ nhập một từ/cụm tiếng Anh, tối đa 12 từ và 120 ký tự." : "Không thể tra từ. Vui lòng thử lại.";
    throw new ApiError(detail, Number(response.headers.get("Retry-After")) || 0);
  }
  return response;
}
