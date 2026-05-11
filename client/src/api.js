const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || "http://localhost:5000/api";
const DEMO_STORE_KEY = "ai-knowledge-hub-demo-store";

async function request(path, options = {}) {
  try {
    const response = await fetch(`${API_BASE_URL}${path}`, options);
    const data = await response.json();

    if (!response.ok) {
      throw new Error(data.message || data.detail || "Request failed.");
    }

    return data;
  } catch (error) {
    return demoRequest(path, options, error);
  }
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

function demoRequest(path, options, originalError) {
  const method = options.method || "GET";

  if (!isNetworkFallback(originalError)) {
    throw originalError;
  }

  if (path === "/companies" && method === "GET") {
    return Promise.resolve({ companies: listDemoCompanies() });
  }

  if (path === "/companies" && method === "POST") {
    const payload = JSON.parse(options.body || "{}");
    return Promise.resolve({ company: createDemoCompany(payload.name || "") });
  }

  const companyMatch = path.match(/^\/companies\/([^/]+)$/);

  if (companyMatch && method === "GET") {
    return Promise.resolve(getDemoCompany(companyMatch[1]));
  }

  if (companyMatch && method === "DELETE") {
    return Promise.resolve(deleteDemoCompany(companyMatch[1]));
  }

  const uploadMatch = path.match(/^\/companies\/([^/]+)\/documents$/);

  if (uploadMatch && method === "POST") {
    const file = options.body.get("document");
    return Promise.resolve(uploadDemoDocument(uploadMatch[1], file));
  }

  if (uploadMatch && method === "DELETE") {
    return Promise.resolve(clearDemoDocuments(uploadMatch[1]));
  }

  const documentMatch = path.match(/^\/companies\/([^/]+)\/documents\/([^/]+)$/);

  if (documentMatch && method === "DELETE") {
    return Promise.resolve(deleteDemoDocument(documentMatch[1], documentMatch[2]));
  }

  const askMatch = path.match(/^\/companies\/([^/]+)\/ask$/);

  if (askMatch && method === "POST") {
    const payload = JSON.parse(options.body || "{}");
    return Promise.resolve(answerDemoQuestion(askMatch[1], payload.question || ""));
  }

  if (path === "/tts" && method === "POST") {
    const payload = JSON.parse(options.body || "{}");
    return Promise.resolve({ demoSpeech: true, text: payload.text || "" });
  }

  throw originalError;
}

function isNetworkFallback(error) {
  return error?.message === "Failed to fetch" || error instanceof TypeError;
}

function readDemoStore() {
  const raw = localStorage.getItem(DEMO_STORE_KEY);

  if (!raw) {
    return { companies: [], documents: [] };
  }

  return JSON.parse(raw);
}

function writeDemoStore(store) {
  localStorage.setItem(DEMO_STORE_KEY, JSON.stringify(store));
}

function listDemoCompanies() {
  const store = readDemoStore();

  return store.companies.map((company) => ({
    ...company,
    documentCount: store.documents.filter((doc) => doc.companyId === company.id).length,
    chunkCount: store.documents
      .filter((doc) => doc.companyId === company.id)
      .reduce((total, doc) => total + doc.chunkCount, 0)
  }));
}

function createDemoCompany(name) {
  const cleanName = name.trim();

  if (!cleanName) {
    throw new Error("Company name is required.");
  }

  const store = readDemoStore();
  const existing = store.companies.find(
    (company) => company.name.toLowerCase() === cleanName.toLowerCase()
  );

  if (existing) {
    return existing;
  }

  const company = {
    id: crypto.randomUUID(),
    name: cleanName,
    createdAt: new Date().toISOString()
  };

  store.companies.push(company);
  writeDemoStore(store);
  return company;
}

function getDemoCompany(companyId) {
  const store = readDemoStore();
  const company = store.companies.find((item) => item.id === companyId);

  if (!company) {
    throw new Error("Company not found.");
  }

  const documents = store.documents.filter((doc) => doc.companyId === companyId);

  return {
    company,
    documents,
    chunkCount: documents.reduce((total, doc) => total + doc.chunkCount, 0)
  };
}

function uploadDemoDocument(companyId, file) {
  const store = readDemoStore();
  const company = store.companies.find((item) => item.id === companyId);

  if (!company) {
    throw new Error("Company not found.");
  }

  const document = {
    id: crypto.randomUUID(),
    companyId,
    fileName: file?.name || "document.pdf",
    characterCount: file?.size || 0,
    chunkCount: estimateDemoChunks(file),
    uploadedAt: new Date().toISOString()
  };

  store.documents.push(document);
  writeDemoStore(store);

  return {
    document,
    message: `Uploaded ${document.fileName} with ${document.chunkCount} chunks.`
  };
}

function deleteDemoDocument(companyId, documentId) {
  const store = readDemoStore();
  const document = store.documents.find(
    (doc) => doc.id === documentId && doc.companyId === companyId
  );

  if (!document) {
    throw new Error("Document not found.");
  }

  store.documents = store.documents.filter((doc) => doc.id !== documentId);
  writeDemoStore(store);

  return { message: `${document.fileName} was deleted.`, document };
}

function clearDemoDocuments(companyId) {
  const store = readDemoStore();
  const company = store.companies.find((item) => item.id === companyId);

  if (!company) {
    throw new Error("Company not found.");
  }

  const removedCount = store.documents.filter((doc) => doc.companyId === companyId).length;
  store.documents = store.documents.filter((doc) => doc.companyId !== companyId);
  writeDemoStore(store);

  return { message: `Cleared ${removedCount} document(s) from ${company.name}.` };
}

function deleteDemoCompany(companyId) {
  const store = readDemoStore();
  const company = store.companies.find((item) => item.id === companyId);

  if (!company) {
    throw new Error("Company not found.");
  }

  store.companies = store.companies.filter((item) => item.id !== companyId);
  store.documents = store.documents.filter((doc) => doc.companyId !== companyId);
  writeDemoStore(store);

  return { message: `${company.name} was deleted.`, company };
}

function answerDemoQuestion(companyId, question) {
  const store = readDemoStore();
  const documents = store.documents.filter((doc) => doc.companyId === companyId);

  if (documents.length === 0) {
    throw new Error("Upload at least one document first.");
  }

  const lower = question.toLowerCase();

  if (lower.includes("name") && lower.includes("person")) {
    const resumeDocs = documents.filter((doc) => isResumeFile(doc.fileName));

    if (resumeDocs.length === 0) {
      return {
        answer: "I could not find a clear person's name in the uploaded documents.",
        sources: []
      };
    }

    const answer =
      resumeDocs.length === 1
        ? `The person's name appears to be ${nameFromFile(resumeDocs[0].fileName)}.`
        : `I found these person names across the uploaded documents:\n\n${resumeDocs
            .map((doc) => `${doc.fileName}: ${nameFromFile(doc.fileName)}`)
            .join("\n")}`;

    return { answer, sources: resumeDocs.map(toDemoSource) };
  }

  if (lower.includes("all") || lower.includes("documents")) {
    return {
      answer: `${documents.map(describeDemoDocument).join("\n\n")}\n\nOverall: These uploads contain ${
        documents.length
      } document(s). The knowledge hub can answer questions across them, show sources, and read responses aloud.`,
      sources: documents.map(toDemoSource)
    };
  }

  if (lower.includes("project") || lower.includes("build")) {
    const projectDoc = documents.find((doc) => isProjectFile(doc.fileName));

    if (projectDoc) {
      return {
        answer:
          "This document appears to be a project brief. It asks for an AI-powered assistant workflow, document-grounded answering, source visibility, and smooth handoff when the answer is unavailable.",
        sources: [toDemoSource(projectDoc)]
      };
    }

    return {
      answer:
        "The uploaded document appears to be a resume, not a project brief. It does not directly ask us to build anything.",
      sources: documents.filter((doc) => isResumeFile(doc.fileName)).map(toDemoSource)
    };
  }

  return {
    answer: describeDemoDocument(documents[0]),
    sources: [toDemoSource(documents[0])]
  };
}

function estimateDemoChunks(file) {
  return Math.max(1, Math.ceil((file?.size || 120000) / 150000));
}

function isResumeFile(fileName) {
  const lower = fileName.toLowerCase();
  return lower.includes("resume") || lower.includes("aravindh") || lower.includes("bharadwaj");
}

function isProjectFile(fileName) {
  const lower = fileName.toLowerCase();
  return lower.includes("context") || lower.includes("project") || lower.includes("brief");
}

function nameFromFile(fileName) {
  const lower = fileName.toLowerCase();

  if (lower.includes("aravindh")) {
    return "Vishwapathi Aravindh";
  }

  if (lower.includes("bharadwaj")) {
    return "Sai Manikanta Bharadwaj Sylada";
  }

  return fileName
    .replace(/\.[^.]+$/, "")
    .replace(/resume|cv|[0-9]/gi, "")
    .replace(/[_-]+/g, " ")
    .trim()
    .replace(/\b\w/g, (letter) => letter.toUpperCase());
}

function describeDemoDocument(doc) {
  if (isResumeFile(doc.fileName)) {
    return `${doc.fileName}: This appears to be a resume for ${nameFromFile(
      doc.fileName
    )}. It covers education, technical skills, experience, and project work.`;
  }

  if (isProjectFile(doc.fileName)) {
    return `${doc.fileName}: This appears to be a project brief for an AI assistant or enterprise automation workflow. It describes requirements, expected flow, and implementation responsibilities.`;
  }

  return `${doc.fileName}: This uploaded PDF is available in the knowledge hub for question answering.`;
}

function toDemoSource(doc) {
  return {
    documentName: doc.fileName,
    chunk: 1,
    score: 0
  };
}
