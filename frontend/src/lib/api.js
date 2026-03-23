const BASE = '/api';

async function request(path, options = {}) {
  const res = await fetch(`${BASE}${path}`, {
    headers: { 'Content-Type': 'application/json', ...options.headers },
    ...options,
  });
  if (!res.ok) {
    const err = await res.json().catch(() => ({ detail: res.statusText }));
    throw new Error(err.detail || `HTTP ${res.status}`);
  }
  if (res.status === 204) return null;
  return res.json();
}

export const api = {
  // --- Owners ---
  getOwners: () => request('/owners/'),
  createOwner: (data) => request('/owners/', { method: 'POST', body: JSON.stringify(data) }),
  updateOwner: (id, data) => request(`/owners/${id}`, { method: 'PUT', body: JSON.stringify(data) }),
  deleteOwner: (id) => request(`/owners/${id}`, { method: 'DELETE' }),

  // --- Accounts ---
  getAccounts: () => request('/accounts/'),
  updateAccount: (id, data) => request(`/accounts/${id}`, { method: 'PUT', body: JSON.stringify(data) }),

  // --- Transactions ---
  getTransactions: (params = {}) => {
    const q = new URLSearchParams(Object.entries(params).filter(([, v]) => v != null));
    return request(`/transactions/?${q}`);
  },

  // --- Analytics ---
  getDashboard: (year) => request(`/analytics/dashboard?year=${year}`),
  getPaymentStatus: (year) => request(`/analytics/payment-status?year=${year}`),
  getSurcharges: () => request('/analytics/surcharges'),
  getExpenses: (year) => request(`/analytics/expenses?year=${year}`),
  getIncome: (year) => request(`/analytics/income?year=${year}`),
  getAccountBalanceHistory: () => request('/analytics/account-balance-history'),

  // --- Abrechnungen ---
  getAbrechnung: (year) => request(`/abrechnungen/${year}`),
  updateAbrechnung: (year, data) => request(`/abrechnungen/${year}`, { method: 'PUT', body: JSON.stringify(data) }),

  // --- Import ---
  seed: () => request('/import/seed', { method: 'POST' }),
  seedFiles: () => request('/import/seed-files', { method: 'POST' }),
  getAvailableFiles: () => request('/import/available-files'),
  importSingleFile: (filename) => {
    const form = new FormData();
    form.append('filename', filename);
    return fetch(`${BASE}/import/import-single`, { method: 'POST', body: form }).then(r => r.json());
  },
  importFile: (file, accountNumber) => {
    const form = new FormData();
    form.append('file', file);
    form.append('account_number', accountNumber);
    return fetch(`${BASE}/import/starmoney`, { method: 'POST', body: form }).then(r => r.json());
  },
};
