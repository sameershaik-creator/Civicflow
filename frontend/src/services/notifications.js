/**
 * CivicFlow Citizen In-App Notification API Service (Phase 10)
 */

import { getStoredToken } from './auth';
import { API_BASE_URL, apiFetch, parseApiResponse } from './api';

function getAuthHeader() {
  const token = getStoredToken();
  if (!token) {
    throw new Error('Your session has expired. Please log in again.');
  }
  return {
    'Accept': 'application/json',
    'Authorization': `Bearer ${token}`,
  };
}

/**
 * Fetch all notifications belonging to the authenticated citizen.
 * Ordered newest first by backend.
 */
export async function fetchNotifications() {
  const headers = getAuthHeader();
  const url = `${API_BASE_URL}/api/v1/notifications`;

  const response = await apiFetch(url, {
    method: 'GET',
    headers,
    timeoutMs: 25000,
  });

  return await parseApiResponse(response);
}

/**
 * Fetch the exact count of unread notifications for the authenticated citizen.
 */
export async function fetchUnreadCount() {
  const token = getStoredToken();
  if (!token) return 0;

  try {
    const headers = getAuthHeader();
    const url = `${API_BASE_URL}/api/v1/notifications/unread-count`;

    const response = await apiFetch(url, {
      method: 'GET',
      headers,
      timeoutMs: 15000,
    });

    const data = await parseApiResponse(response);
    return data?.unread_count || 0;
  } catch {
    return 0;
  }
}

/**
 * Fetch a single notification by ID.
 */
export async function fetchNotificationDetail(notificationId) {
  const headers = getAuthHeader();
  const url = `${API_BASE_URL}/api/v1/notifications/${notificationId}`;

  const response = await apiFetch(url, {
    method: 'GET',
    headers,
    timeoutMs: 25000,
  });

  return await parseApiResponse(response);
}

/**
 * Mark a notification as read. Idempotent.
 */
export async function markNotificationRead(notificationId) {
  const headers = getAuthHeader();
  const url = `${API_BASE_URL}/api/v1/notifications/${notificationId}/read`;

  const response = await apiFetch(url, {
    method: 'PATCH',
    headers,
    timeoutMs: 20000,
  });

  return await parseApiResponse(response);
}
