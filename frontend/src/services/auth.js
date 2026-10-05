/**
 * CivicFlow Minimal Authentication Client Service
 * Provides token storage and API requests for register, login, and profile fetching.
 */

import { API_BASE_URL, apiFetch, parseApiResponse } from './api';

const TOKEN_KEY = 'civicflow_auth_token';

export function getStoredToken() {
  try {
    return localStorage.getItem(TOKEN_KEY);
  } catch {
    return null;
  }
}

export function setStoredToken(token) {
  try {
    if (token) {
      localStorage.setItem(TOKEN_KEY, token);
    } else {
      localStorage.removeItem(TOKEN_KEY);
    }
  } catch {
    // Storage access might be restricted in some environments
  }
}

export function clearStoredToken() {
  try {
    localStorage.removeItem(TOKEN_KEY);
  } catch {
    // No-op
  }
}

export function getAuthHeaders() {
  const token = getStoredToken();
  const headers = {
    'Accept': 'application/json',
    'Content-Type': 'application/json',
  };
  if (token) {
    headers['Authorization'] = `Bearer ${token}`;
  }
  return headers;
}

export async function registerUser({ name, email, password }) {
  const response = await apiFetch(`${API_BASE_URL}/api/v1/auth/register`, {
    method: 'POST',
    headers: {
      'Accept': 'application/json',
      'Content-Type': 'application/json',
    },
    body: JSON.stringify({ name, email, password }),
  });

  const data = await parseApiResponse(response);

  if (data?.access_token) {
    setStoredToken(data.access_token);
  }
  return data;
}

export async function loginUser({ email, password }) {
  const response = await apiFetch(`${API_BASE_URL}/api/v1/auth/login`, {
    method: 'POST',
    headers: {
      'Accept': 'application/json',
      'Content-Type': 'application/json',
    },
    body: JSON.stringify({ email, password }),
  });

  const data = await parseApiResponse(response);

  if (data?.access_token) {
    setStoredToken(data.access_token);
  }
  return data;
}

export async function fetchCurrentUser() {
  const token = getStoredToken();
  if (!token) return null;

  try {
    const response = await apiFetch(`${API_BASE_URL}/api/v1/auth/me`, {
      method: 'GET',
      headers: getAuthHeaders(),
      timeoutMs: 15000,
    });

    if (response.status === 401) {
      clearStoredToken();
      return null;
    }

    return await parseApiResponse(response);
  } catch {
    return null;
  }
}

