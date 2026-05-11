const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || "http://localhost:5000/api";

async function request(path, options = {}) {
  const response = await fetch(`${API_BASE_URL}${path}`, options);
  const data = await response.json();

  if (!response.ok) {
    throw new Error(data.message || "Request failed.");
  }

  return data;
}

export function getCompanies() {
  return request("/companies");
}

export function createCompany(name) {
  return request("/companies", {
    method: "POST",
    headers: {
      "Content-Type": "application/json"
    },
    body: JSON.stringify({ name })
  });
}

export function getCompany(companyId) {
  return request(`/companies/${companyId}`);
}

export function uploadDocument(companyId, file) {
  const formData = new FormData();
  formData.append("document", file);

  return request(`/companies/${companyId}/documents`, {
    method: "POST",
    body: formData
  });
}

export function deleteDocument(companyId, documentId) {
  return request(`/companies/${companyId}/documents/${documentId}`, {
    method: "DELETE"
  });
}

export function clearDocuments(companyId) {
  return request(`/companies/${companyId}/documents`, {
    method: "DELETE"
  });
}

export function deleteCompany(companyId) {
  return request(`/companies/${companyId}`, {
    method: "DELETE"
  });
}

export function askQuestion(companyId, question) {
  return request(`/companies/${companyId}/ask`, {
    method: "POST",
    headers: {
      "Content-Type": "application/json"
    },
    body: JSON.stringify({ question })
  });
}

export function generateSpeech(text) {
  return request("/tts", {
    method: "POST",
    headers: {
      "Content-Type": "application/json"
    },
    body: JSON.stringify({ text })
  });
}
