const API_BASE_URL = import.meta.env.VITE_API_URL || 'http://127.0.0.1:8000';

async function handleResponse(response) {
  if (!response.ok) {
    const errorBody = await response.json().catch(() => ({}));
    const detail = errorBody.detail || response.statusText;
    throw new Error(Array.isArray(detail) ? detail.join(', ') : detail);
  }
  return response.json();
}

export async function postTrace(payload) {
  const response = await fetch(`${API_BASE_URL}/trace`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(payload),
  });
  return handleResponse(response);
}

export async function fetchAlerts(limit = 25) {
  const response = await fetch(`${API_BASE_URL}/alerts?limit=${limit}`);
  return handleResponse(response);
}

export async function ingestAddressTransactions(address) {
  const normalized = address?.trim();
  if (!normalized) {
    throw new Error('Ethereum address is required');
  }

  const response = await fetch(`${API_BASE_URL}/ingest/${encodeURIComponent(normalized)}`);
  return handleResponse(response);
}

export async function refreshAlerts(contamination = 0.05) {
  const url = new URL(`${API_BASE_URL}/alerts/refresh`);
  url.searchParams.set('contamination', contamination.toString());
  const response = await fetch(url, { method: 'POST' });
  return handleResponse(response);
}

export async function fetchAddress(address) {
  const response = await fetch(`${API_BASE_URL}/address/${address}`);
  return handleResponse(response);
}

export async function triggerClustering(batchSize = 50) {
  const response = await fetch(`${API_BASE_URL}/address/cluster`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ batch_size: batchSize }),
  });
  return handleResponse(response);
}

export async function uploadBlacklist(file) {
  const formData = new FormData();
  formData.append('file', file);

  const response = await fetch(`${API_BASE_URL}/compliance/blacklist`, {
    method: 'POST',
    body: formData,
  });
  return handleResponse(response);
}

export async function recomputeSeverity() {
  const response = await fetch(`${API_BASE_URL}/compliance/severity`, {
    method: 'POST',
  });
  return handleResponse(response);
}
