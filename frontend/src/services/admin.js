/**
 * CivicFlow Municipal Administrator Adjudication API Service (Phase 9)
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

export async function fetchAdminComplaints(status = 'SUBMITTED') {
  const headers = getAuthHeader();
  const url = `${API_BASE_URL}/api/v1/admin/complaints?status=${encodeURIComponent(status)}`;

  const response = await apiFetch(url, {
    method: 'GET',
    headers,
    timeoutMs: 25000,
  });

  return await parseApiResponse(response);
}

export async function fetchAdminComplaintDetail(complaintId) {
  const headers = getAuthHeader();
  const url = `${API_BASE_URL}/api/v1/admin/complaints/${complaintId}`;

  const response = await apiFetch(url, {
    method: 'GET',
    headers,
    timeoutMs: 25000,
  });

  return await parseApiResponse(response);
}

export async function acceptComplaint(complaintId) {
  const headers = getAuthHeader();
  const url = `${API_BASE_URL}/api/v1/admin/complaints/${complaintId}/accept`;

  const response = await apiFetch(url, {
    method: 'POST',
    headers,
    timeoutMs: 30000,
  });

  return await parseApiResponse(response);
}

export async function rejectComplaint(complaintId, { admin_reason }) {
  const headers = {
    ...getAuthHeader(),
    'Content-Type': 'application/json',
  };
  const url = `${API_BASE_URL}/api/v1/admin/complaints/${complaintId}/reject`;

  const response = await apiFetch(url, {
    method: 'POST',
    headers,
    body: JSON.stringify({ admin_reason }),
    timeoutMs: 30000,
  });

  return await parseApiResponse(response);
}
