/**
 * CivicFlow API Service Abstraction
 * Centralizes all network communication with the backend.
 */

const rawApiUrl = import.meta.env.VITE_API_URL;
const API_BASE_URL = (rawApiUrl && rawApiUrl.trim()) 
  ? rawApiUrl.trim().replace(/\/+$/, '') 
  : 'http://localhost:8000';

export async function parseApiResponse(response) {
  const contentType = response.headers.get('content-type') || '';
  let data = null;
  if (contentType.includes('application/json')) {
    try {
      data = await response.json();
    } catch {
      data = null;
    }
  } else {
    try {
      const text = await response.text();
      data = { detail: text };
    } catch {
      data = null;
    }
  }

  if (!response.ok) {
    if (response.status === 502 || response.status === 503 || response.status === 504) {
      throw new Error(
        "Backend server is waking up from free-tier sleep (Render cold start). Please wait ~30-45 seconds and try again."
      );
    }
    if (response.status === 429) {
      throw new Error(
        data?.detail || "Rate limit or quota exceeded (HTTP 429). Please wait a moment before retrying."
      );
    }
    const message = data?.detail || data?.message || `Server error (HTTP ${response.status})`;
    throw new Error(typeof message === 'string' ? message : JSON.stringify(message));
  }

  return data;
}

export async function apiFetch(url, options = {}) {
  const controller = new AbortController();
  const timeoutMs = options.timeoutMs || 45000;
  const timeoutId = setTimeout(() => controller.abort(), timeoutMs);

  try {
    const response = await fetch(url, {
      ...options,
      signal: options.signal || controller.signal,
    });
    return response;
  } catch (error) {
    if (error.name === 'AbortError') {
      throw new Error("Request timed out. The free server may be waking up from idle. Please try again.");
    }
    if (error.message?.includes('Failed to fetch') || error.message?.includes('NetworkError')) {
      throw new Error("Unable to connect to server. The backend may be spinning up from idle (Render cold start). Please retry in 30 seconds.");
    }
    throw error;
  } finally {
    clearTimeout(timeoutId);
  }
}

export async function checkBackendHealth() {
  try {
    const startTime = performance.now();
    const response = await apiFetch(`${API_BASE_URL}/health`, {
      method: 'GET',
      headers: {
        'Accept': 'application/json',
      },
      timeoutMs: 15000,
    });

    const elapsedMs = Math.round(performance.now() - startTime);

    if (!response.ok) {
      const isColdStart = response.status === 502 || response.status === 503;
      return {
        ok: false,
        status: response.status,
        data: null,
        error: isColdStart 
          ? "Server waking up from free-tier sleep (~30-50s cold start)..." 
          : `HTTP ${response.status}: ${response.statusText}`,
        elapsedMs,
      };
    }

    const data = await response.json();
    return {
      ok: true,
      status: response.status,
      data,
      error: null,
      elapsedMs,
    };
  } catch (error) {
    return {
      ok: false,
      status: 0,
      data: null,
      error: error.message || 'Unable to connect to backend service',
      elapsedMs: 0,
    };
  }
}

export async function checkDatabaseHealth() {
  try {
    const response = await apiFetch(`${API_BASE_URL}/health/db`, {
      method: 'GET',
      headers: {
        'Accept': 'application/json',
      },
      timeoutMs: 15000,
    });

    if (!response.ok) {
      return {
        ok: false,
        status: response.status,
        data: null,
        error: `HTTP ${response.status}: ${response.statusText}`,
      };
    }

    const data = await response.json();
    return {
      ok: true,
      status: response.status,
      data,
      error: null,
    };
  } catch (error) {
    return {
      ok: false,
      status: 0,
      data: null,
      error: error.message || 'Database health check failed',
    };
  }
}

export async function getRootInfo() {
  try {
    const response = await apiFetch(`${API_BASE_URL}/`, {
      method: 'GET',
      headers: {
        'Accept': 'application/json',
      },
      timeoutMs: 10000,
    });
    if (!response.ok) return null;
    return await response.json();
  } catch {
    return null;
  }
}

export { API_BASE_URL };

