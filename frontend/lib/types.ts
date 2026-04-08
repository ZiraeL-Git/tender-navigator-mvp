export type CompanyProfile = {
  id: number;
  created_at: string;
  company_name: string;
  inn: string;
  region: string;
  categories: string[];
  has_license: boolean;
  has_experience: boolean;
  can_prepare_fast: boolean;
  notes: string;
};

export type CompanyProfilePayload = Omit<CompanyProfile, "id" | "created_at">;

export type TenderInput = {
  id: number;
  created_at: string;
  updated_at: string;
  company_profile_id: number;
  source_type: string;
  source_value: string;
  source_url: string | null;
  notice_number: string | null;
  title: string;
  customer_name: string | null;
  deadline: string | null;
  max_price: string | null;
  status: string;
  normalized_payload: Record<string, unknown>;
  documents: Array<{
    filename: string;
    content_type: string;
    size: number;
    kind: string;
  }>;
  last_error: string | null;
  latest_analysis_id: number | null;
};

export type TenderInputListItem = {
  id: number;
  created_at: string;
  company_profile_id: number;
  source_type: string;
  source_value: string;
  title: string;
  status: string;
  notice_number: string | null;
  latest_analysis_id: number | null;
  document_count: number;
};

export type Analysis = {
  id: number;
  created_at: string;
  company_profile_id: number;
  tender_input_id: number | null;
  package_name: string;
  status: string;
  background_task_id: string | null;
  failure_reason: string | null;
  started_at: string | null;
  completed_at: string | null;
  ai_summary_requested: boolean;
  raw_text: string | null;
  extracted: Record<string, string | boolean | null>;
  decision_code: string | null;
  decision_label: string | null;
  decision_reasons: Array<{
    code: string;
    severity: string;
    message: string;
    rule_id: string;
    rule_title: string;
    decision_code: string;
  }>;
  checklist: string[];
  ai_summary: string | null;
  documents: Array<{
    filename: string;
    doc_type: string;
    extracted_text: string | null;
    text_length: number;
  }>;
  warnings: string[];
  errors: string[];
  events: Array<{
    event_type: string;
    payload: Record<string, unknown>;
    created_at: string;
  }>;
};

export type AnalysisListItem = {
  id: number;
  created_at: string;
  company_profile_id: number;
  tender_input_id: number | null;
  package_name: string;
  status: string;
  background_task_id: string | null;
  decision_code: string | null;
  decision_label: string | null;
  notice_number: string | null;
  object_name: string | null;
  deadline: string | null;
};

export type DashboardMetrics = {
  analysesCount: number;
  inputsCount: number;
  activeProfileName: string;
};
