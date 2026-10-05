/**
 * CivicFlow Complaint API Client (Phase 4)
 * Handles citizen complaint draft creation (with image upload) and retrieval.
 */

import { API_BASE_URL, apiFetch, parseApiResponse } from './api';
import { getStoredToken } from './auth';

export async function createComplaintDraft({ imageFile, problem, address, latitude, longitude }) {
  const token = getStoredToken();
  if (!token) {
    throw new Error('Authentication required. Please log in before creating a complaint.');
  }

  const formData = new FormData();
  formData.append('image', imageFile);
  formData.append('original_problem', problem);

  if (address && address.trim()) {
    formData.append('original_address', address.trim());
  }
  if (latitude !== undefined && latitude !== null && latitude !== '') {
    formData.append('original_latitude', parseFloat(latitude));
  }
  if (longitude !== undefined && longitude !== null && longitude !== '') {
    formData.append('original_longitude', parseFloat(longitude));
  }

  const response = await apiFetch(`${API_BASE_URL}/api/v1/complaints/analyze`, {
    method: 'POST',
    headers: {
      'Accept': 'application/json',
      'Authorization': `Bearer ${token}`,
      // Note: Do not manually set Content-Type header when sending FormData; browser sets boundary automatically
    },
    body: formData,
    timeoutMs: 45000,
  });

  return await parseApiResponse(response);
}

export async function fetchMyComplaints() {
  const token = getStoredToken();
  if (!token) {
    return [];
  }

  const response = await apiFetch(`${API_BASE_URL}/api/v1/complaints`, {
    method: 'GET',
    headers: {
      'Accept': 'application/json',
      'Authorization': `Bearer ${token}`,
    },
    timeoutMs: 25000,
  });

  return await parseApiResponse(response);
}

export async function fetchComplaintById(complaintId) {
  const token = getStoredToken();
  if (!token) {
    throw new Error('Authentication required.');
  }

  const response = await apiFetch(`${API_BASE_URL}/api/v1/complaints/${complaintId}`, {
    method: 'GET',
    headers: {
      'Accept': 'application/json',
      'Authorization': `Bearer ${token}`,
    },
    timeoutMs: 25000,
  });

  return await parseApiResponse(response);
}

export async function analyzeComplaintWithAI(complaintId) {
  const token = getStoredToken();
  if (!token) {
    throw new Error('Authentication required.');
  }

  const response = await apiFetch(`${API_BASE_URL}/api/v1/complaints/${complaintId}/analyze`, {
    method: 'POST',
    headers: {
      'Accept': 'application/json',
      'Authorization': `Bearer ${token}`,
    },
    timeoutMs: 45000,
  });

  return await parseApiResponse(response);
}

export async function verifyComplaintLocation(complaintId) {
  const token = getStoredToken();
  if (!token) {
    throw new Error('Authentication required.');
  }

  const response = await apiFetch(`${API_BASE_URL}/api/v1/complaints/${complaintId}/location/verify`, {
    method: 'POST',
    headers: {
      'Accept': 'application/json',
      'Authorization': `Bearer ${token}`,
    },
    timeoutMs: 25000,
  });

  return await parseApiResponse(response);
}

export async function getComplaintLocation(complaintId) {
  const token = getStoredToken();
  if (!token) {
    throw new Error('Authentication required.');
  }

  const response = await apiFetch(`${API_BASE_URL}/api/v1/complaints/${complaintId}/location`, {
    method: 'GET',
    headers: {
      'Accept': 'application/json',
      'Authorization': `Bearer ${token}`,
    },
    timeoutMs: 20000,
  });

  return await parseApiResponse(response);
}

export async function getComplaintAIDraft(complaintId) {
  const token = getStoredToken();
  if (!token) {
    throw new Error('Authentication required.');
  }

  const response = await apiFetch(`${API_BASE_URL}/api/v1/complaints/${complaintId}/ai-draft`, {
    method: 'GET',
    headers: {
      'Accept': 'application/json',
      'Authorization': `Bearer ${token}`,
    },
    timeoutMs: 20000,
  });

  return await parseApiResponse(response);
}

export async function updateComplaintDraft(complaintId, { final_problem, final_address, final_summary }) {
  const token = getStoredToken();
  if (!token) {
    throw new Error('Authentication required.');
  }

  const payload = {
    final_problem: final_problem ? final_problem.trim() : '',
  };
  if (final_address !== undefined && final_address !== null) {
    payload.final_address = final_address.trim() || null;
  }
  if (final_summary !== undefined && final_summary !== null) {
    payload.final_summary = final_summary.trim() || null;
  }

  const response = await apiFetch(`${API_BASE_URL}/api/v1/complaints/${complaintId}/draft`, {
    method: 'PUT',
    headers: {
      'Content-Type': 'application/json',
      'Accept': 'application/json',
      'Authorization': `Bearer ${token}`,
    },
    body: JSON.stringify(payload),
    timeoutMs: 25000,
  });

  return await parseApiResponse(response);
}

export async function fetchComplaintImageBlob(complaintId) {
  const token = getStoredToken();
  if (!token) {
    throw new Error('Authentication required.');
  }

  const response = await apiFetch(`${API_BASE_URL}/api/v1/complaints/${complaintId}/image`, {
    method: 'GET',
    headers: {
      'Authorization': `Bearer ${token}`,
    },
    timeoutMs: 30000,
  });

  if (!response.ok) {
    if (response.status === 502 || response.status === 503) {
      throw new Error("Server waking up (cold start). Please retry in a moment.");
    }
    throw new Error(`Failed to load evidence image (HTTP ${response.status})`);
  }

  return await response.blob();
}

export async function submitComplaint(complaintId) {
  const token = getStoredToken();
  if (!token) {
    throw new Error('Your session has expired. Please log in again.');
  }

  const response = await apiFetch(`${API_BASE_URL}/api/v1/complaints/${complaintId}/submit`, {
    method: 'POST',
    headers: {
      'Accept': 'application/json',
      'Authorization': `Bearer ${token}`,
    },
    timeoutMs: 30000,
  });

  return await parseApiResponse(response);
}

export async function deleteComplaintById(complaintId) {
  const token = getStoredToken();
  if (!token) {
    throw new Error('Authentication required. Please log in.');
  }

  const response = await apiFetch(`${API_BASE_URL}/api/v1/complaints/${complaintId}`, {
    method: 'DELETE',
    headers: {
      'Accept': 'application/json',
      'Authorization': `Bearer ${token}`,
    },
    timeoutMs: 25000,
  });

  return await parseApiResponse(response);
}
