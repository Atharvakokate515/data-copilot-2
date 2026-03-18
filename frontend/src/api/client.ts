const BASE = "http://localhost:8000";

async function request<T>(path: string, options?: RequestInit): Promise<T> {
  const res = await fetch(`${BASE}${path}`, {
    headers: { "Content-Type": "application/json", ...options?.headers },
    ...options,
  });
  if (!res.ok) throw new Error(`HTTP ${res.status}: ${res.statusText}`);
  return res.json();
}

// NL2SQL
export const testConnection = (db_url: string) =>
  request<any>("/api/test-connection", { method: "POST", body: JSON.stringify({ db_url }) });

export const chatDB = (db_url: string, user_input: string, session_id: string, clarification_response?: string) =>
  request<any>("/api/chat-db", {
    method: "POST",
    body: JSON.stringify({ db_url, user_input, session_id, ...(clarification_response ? { clarification_response } : {}) }),
  });

export const getNL2SQLSessions = () => request<any[]>("/api/nl2sql-sessions");

export const getSessionHistory = (session_id: string) => request<any>(`/api/session-history/${session_id}`);

export const deleteNL2SQLSession = (session_id: string) =>
  request<any>(`/api/nl2sql-sessions/${session_id}`, { method: "DELETE" });

// Copilot
export const createChat = (title?: string) =>
  request<any>("/api/create-chat", { method: "POST", body: JSON.stringify({ title: title || "New Copilot Chat" }) });

export const agentChat = (db_url: string, user_input: string, chat_id: number) =>
  request<any>("/api/agent-chat", { method: "POST", body: JSON.stringify({ db_url, user_input, chat_id }) });

export const getCopilotSessions = () => request<any[]>("/api/copilot-sessions");

export const getCopilotHistory = (chat_id: number) => request<any>(`/api/copilot-history/${chat_id}`);

export const deleteCopilotSession = (chat_id: number) =>
  request<any>(`/api/copilot-sessions/${chat_id}`, { method: "DELETE" });

// Documents
export const uploadDoc = (file: File) => {
  const form = new FormData();
  form.append("file", file);
  return fetch(`${BASE}/api/upload-doc`, { method: "POST", body: form }).then((r) => r.json());
};

export const getDocs = () => request<any>("/api/docs");

export const deleteDoc = (source: string) =>
  request<any>(`/api/docs/${encodeURIComponent(source)}`, { method: "DELETE" });
