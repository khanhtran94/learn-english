export const API_URL = import.meta.env.VITE_API_URL ?? "http://localhost:8000";

export class ApiError extends Error {
  retryAfter: number;
  constructor(message: string, retryAfter = 0) {
    super(message);
    this.retryAfter = retryAfter;
  }
}

export async function dictionaryRequest(path: "lookup" | "audio", term: string, signal: AbortSignal) {
  const response = await fetch(`${API_URL}/dictionary/${path}`, {
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
