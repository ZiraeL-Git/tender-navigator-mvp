import {
  Analysis,
  AnalysisListItem,
  CompanyProfile,
  CompanyProfilePayload,
  TenderInput,
  TenderInputListItem
} from "@/lib/types";

const API_BASE = process.env.NEXT_PUBLIC_API_BASE_URL ?? "/api/v1";

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  const response = await fetch(`${API_BASE}${path}`, {
    ...init,
    headers: {
      ...(init?.body instanceof FormData ? {} : { "Content-Type": "application/json" }),
      ...init?.headers
    },
    cache: "no-store"
  });

  if (!response.ok) {
    const detail = await response.text();
    throw new Error(detail || `Request failed: ${response.status}`);
  }

  return response.json() as Promise<T>;
}

export const api = {
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
    files.forEach((file) => formData.append("files", file));
    const response = await fetch(
      `${API_BASE}/analyses/from-files?company_profile_id=${companyProfileId}&include_ai_summary=${includeAiSummary}`,
      {
        method: "POST",
        body: formData
      }
    );

    if (!response.ok) {
      throw new Error(await response.text());
    }

    return (await response.json()) as Analysis;
  }
};
