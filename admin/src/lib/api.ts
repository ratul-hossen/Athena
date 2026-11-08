const API_BASE = process.env.NEXT_PUBLIC_API_URL || "https://athena-4i17.onrender.com";

export function getAdminToken(): string {
  if (typeof window !== "undefined") {
    const stored = localStorage.getItem("athina_admin_secret");
    if (stored) return stored;
  }
  return process.env.NEXT_PUBLIC_ADMIN_SECRET || "";
}

export function setAdminToken(token: string) {
  if (typeof window !== "undefined") {
    localStorage.setItem("athina_admin_secret", token.trim());
  }
}

async function request<T>(endpoint: string, options: RequestInit = {}): Promise<T> {
  const token = getAdminToken();
  const headers = {
    "Content-Type": "application/json",
    "Authorization": `Bearer ${token}`,
    ...(options.headers || {}),
  };

  const res = await fetch(`${API_BASE}${endpoint}`, {
    ...options,
    headers,
  });

  if (!res.ok) {
    const errorText = await res.text();
    if (res.status === 401 || res.status === 403) {
      if (typeof window !== "undefined") {
        window.dispatchEvent(new CustomEvent("athina_auth_required"));
      }
    }
    throw new Error(`API error (${res.status}): ${errorText}`);
  }

  return res.json();
}

export interface IdentityConfig {
  its_name: string;
  my_name: string;
  call_me: string;
  persona: string;
  physical_structure?: string;
  personality: string;
  communication_style: string;
  rules: string;
  context: string;
}

export interface RagKnowledgeItem {
  id: string;
  fact: string;
  category: string;
  importance: number;
  created_at?: string;
  has_embedding?: boolean;
}

export const adminApi = {
  getOverview: () => request<any>("/api/admin/overview"),
  
  // Identity & Persona Customization (matching Mercy UI)
  getIdentity: () => request<{ config: IdentityConfig; generated_system_prompt: string }>("/api/admin/identity"),
  updateIdentity: (data: IdentityConfig) =>
    request<{ status: string; config: IdentityConfig; generated_system_prompt: string }>("/api/admin/identity", {
      method: "POST",
      body: JSON.stringify(data),
    }),
  resetIdentity: () =>
    request<{ status: string; config: IdentityConfig; generated_system_prompt: string }>("/api/admin/identity/reset", {
      method: "POST",
    }),

  // Prompt View & Fallback
  getPrompt: () => request<any>("/api/admin/prompt"),
  updatePrompt: (data: { custom_instructions: string; mood_override?: string; location_override?: string }) =>
    request<any>("/api/admin/prompt", {
      method: "POST",
      body: JSON.stringify(data),
    }),

  // Knowledge & RAG Base
  getRagKnowledge: () => request<RagKnowledgeItem[]>("/api/admin/rag"),
  addRagKnowledge: (data: { fact: string; category?: string; importance?: number }) =>
    request<any>("/api/admin/rag", {
      method: "POST",
      body: JSON.stringify(data),
    }),
  updateRagKnowledge: (id: string, data: { fact: string; category?: string; importance?: number }) =>
    request<any>(`/api/admin/rag/${id}`, {
      method: "PUT",
      body: JSON.stringify(data),
    }),
  deleteRagKnowledge: (id: string) =>
    request<any>(`/api/admin/rag/${id}`, {
      method: "DELETE",
    }),
  testRagQuery: (query: string, top_k: number = 5) =>
    request<{ query: string; matched_count: number; results: string[] }>("/api/admin/rag/test", {
      method: "POST",
      body: JSON.stringify({ query, top_k }),
    }),

  // KeyPool
  resetKeypoolCooldowns: () =>
    request<{ status: string }>("/api/admin/keypool/reset", {
      method: "POST",
    }),

  // Memories
  getMemories: () => request<any[]>("/api/memories"),
  deleteMemory: (id: string) =>
    request<any>(`/api/memories/${id}`, {
      method: "DELETE",
    }),

  // Notes & Alarms
  getNotes: () => request<any[]>("/api/notes"),
  uploadNoteTelegram: (id: string) =>
    request<any>(`/api/notes/${id}/upload_telegram`, {
      method: "POST",
    }),
  getAlarms: () => request<any[]>("/api/alarms"),
};
