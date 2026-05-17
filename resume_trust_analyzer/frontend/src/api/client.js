const API_URL = import.meta.env.VITE_API_URL || 'http://localhost:8000';

export async function request(path, options = {}) {
  let response;

  try {
    response = await fetch(`${API_URL}${path}`, {
      headers: {
        'Content-Type': 'application/json',
        ...(options.headers || {}),
      },
      ...options,
    });
  } catch (error) {
    throw new Error(
      `API недоступен по адресу ${API_URL}. Запустите backend: python -m uvicorn app.main:app --reload`
    );
  }

  const contentType = response.headers.get('content-type') || '';
  const isJson = contentType.includes('application/json');

  if (!response.ok) {
    const errorBody = isJson ? await response.json().catch(() => ({})) : {};
    throw new Error(errorBody.detail || `Ошибка API: ${response.status}`);
  }

  // 204 No Content — нет тела ответа
  if (response.status === 204) return null;

  if (!isJson) {
    throw new Error(`API вернул не JSON для ${path}. Проверьте VITE_API_URL и адрес backend.`);
  }

  return response.json();
}

export const api = {
  getCandidates: () => request('/api/candidates'),
  getFilteredCandidates: (riskType) => request(`/api/candidates/filter/by-risk?risk_type=${riskType}`),
  createCandidate: (payload) =>
    request('/api/candidates', {
      method: 'POST',
      body: JSON.stringify(payload),
    }),
  importCandidatesCsv: async (file) => {
    const formData = new FormData();
    formData.append('file', file);
    
    const response = await fetch(`${API_URL}/api/candidates/import/csv`, {
      method: 'POST',
      body: formData,
    });
    
    const contentType = response.headers.get('content-type') || '';
    const isJson = contentType.includes('application/json');
    
    if (!response.ok) {
      const errorBody = isJson ? await response.json().catch(() => ({})) : {};
      throw new Error(errorBody.detail || `Ошибка API: ${response.status}`);
    }
    
    return response.json();
  },
  deleteCandidate: (candidateId) =>
    request(`/api/candidates/${candidateId}`, { method: 'DELETE' }),
  getExperiences: (candidateId) => request(`/api/candidates/${candidateId}/experiences`),
  getProfiles: (candidateId) => request(`/api/candidates/${candidateId}/profiles`),
  runCheck: (candidateId) =>
    request(`/api/checks/${candidateId}/run`, {
      method: 'POST',
    }),
};
