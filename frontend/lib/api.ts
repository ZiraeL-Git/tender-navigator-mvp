import { clearSession, getAccessToken } from "@/components/auth";
import {
  Analysis,
  AnalysisListItem,
  AuditLog,
  AuthBootstrap,
  AuthSession,
  AuthUser,
  CompanyProfile,
  CompanyProfilePayload,
  Invitation,
  TenderInput,
  TenderInputListItem
} from "@/lib/types";

const API_BASE = process.env.NEXT_PUBLIC_API_BASE_URL ?? "/api/v1";

type RequestOptions = RequestInit & {
  auth?: boolean;
};

async function request<T>(path: string, init?: RequestOptions): Promise<T> {
  const token = init?.auth === false ? null : getAccessToken();
  const response = await fetch(`${API_BASE}${path}`, {
    ...init,
    headers: {
      ...(token ? { Authorization: `Bearer ${token}` } : {}),
      ...(init?.body instanceof FormData ? {} : { "Content-Type": "application/json" }),
      ...init?.headers
    },
    cache: "no-store"
  });

  if (response.status === 401) {
    clearSession();
    if (typeof window !== "undefined" && window.location.pathname !== "/login") {
      window.location.href = "/login";
    }
  }

  if (!response.ok) {
    const detail = await response.text();
    throw new Error(detail || `Request failed: ${response.status}`);
  }

  return response.json() as Promise<T>;
}

export const api = {
  getBootstrapStatus: () => request<AuthBootstrap>("/auth/bootstrap", { auth: false }),
  register: (payload: {
    organization_name: string;
    full_name: string;
    email: string;
    password: string;
  }) =>
    request<AuthSession>("/auth/register", {
      method: "POST",
      body: JSON.stringify(payload),
      auth: false
    }),
  login: (payload: { email: string; password: string }) =>
    request<AuthSession>("/auth/login", {
      method: "POST",
      body: JSON.stringify(payload),
      auth: false
    }),
  getInvitation: (token: string) => request<Invitation>(`/auth/invitations/${token}`, { auth: false }),
  acceptInvitation: (payload: { token: string; full_name: string; password: string }) =>
    request<AuthSession>("/auth/accept-invitation", {
      method: "POST",
      body: JSON.stringify(payload),
      auth: false
    }),
  getMe: () => request<AuthUser>("/auth/me"),
  listOrganizationUsers: () => request<AuthUser[]>("/organization/users"),
  listInvitations: () => request<Invitation[]>("/organization/invitations"),
  createInvitation: (payload: { email: string; role: "owner" | "operator" | "viewer" }) =>
    request<Invitation>("/organization/invitations", {
      method: "POST",
      body: JSON.stringify(payload)
    }),
  listAuditLogs: (limit = 50) => request<AuditLog[]>(`/audit-logs?limit=${limit}`),
  listCompanyProfiles: () => request<CompanyProfile[]>("/company-profiles"),
  createCompanyProfile: (payload: CompanyProfilePayload) =>
    request<CompanyProfile>("/company-profiles", {
      method: "POST",
      body: JSON.stringify(payload)
    }),
  updateCompanyProfile: (id: number, payload: CompanyProfilePayload) =>
    request<CompanyProfile>(`/company-profiles/${id}`, {
      method: "PUT",
      body: JSON.stringify(payload)
    }),
  getCompanyProfile: (id: number) => request<CompanyProfile>(`/company-profiles/${id}`),
  listAnalyses: () => request<AnalysisListItem[]>("/analyses"),
  getAnalysis: (id: number) => request<Analysis>(`/analyses/${id}`),
  patchManualCorrection: (id: number, payload: unknown) =>
    request<Analysis>(`/analyses/${id}/manual-correction`, {
      method: "PATCH",
      body: JSON.stringify(payload)
    }),
  listTenderInputs: () => request<TenderInputListItem[]>("/tender-inputs"),
  getTenderInput: (id: number) => request<TenderInput>(`/tender-inputs/${id}`),
  importTenderInput: (payload: unknown) =>
    request<TenderInput>("/tender-inputs/import", {
      method: "POST",
      body: JSON.stringify(payload)
    }),
  queueAnalysisFromTenderInput: (id: number, payload: { include_ai_summary: boolean }) =>
    request<Analysis>(`/analyses/from-tender-input/${id}`, {
      method: "POST",
      body: JSON.stringify(payload)
    }),
  createAnalysisFromFiles: async (
    companyProfileId: number,
    files: File[],
    includeAiSummary: boolean
  ) => {
    const formData = new FormData();
    const token = getAccessToken();
    files.forEach((file) => formData.append("files", file));
    const response = await fetch(
      `${API_BASE}/analyses/from-files?company_profile_id=${companyProfileId}&include_ai_summary=${includeAiSummary}`,
      {
        method: "POST",
        body: formData,
        headers: token ? { Authorization: `Bearer ${token}` } : undefined
      }
    );

    if (response.status === 401) {
      clearSession();
      if (typeof window !== "undefined" && window.location.pathname !== "/login") {
        window.location.href = "/login";
      }
    }

    if (!response.ok) {
      throw new Error(await response.text());
    }

    return (await response.json()) as Analysis;
  }
};
