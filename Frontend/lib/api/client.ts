const API_BASE_URL = process.env.NEXT_PUBLIC_API_URL || '';

export async function apiFetch<T>(endpoint: string, options?: RequestInit): Promise<T> {
  if (!API_BASE_URL) {
    // Return null or handle via mock fallback
    throw new Error('NO_BACKEND_URL');
  }

  const res = await fetch(`${API_BASE_URL}${endpoint}`, {
    headers: {
      'Content-Type': 'application/json',
      ...options?.headers,
    },
    ...options,
  });

  if (!res.ok) {
    const errorData = await res.json().catch(() => ({}));
    throw new Error(errorData.message || `API call failed with status ${res.status}`);
  }

  return res.json() as Promise<T>;
}
