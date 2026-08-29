/** Typed client for the HairGPT API. Tokens live in memory + localStorage. */

export type Confidence = { value: number; basis: string; method: string };

export type QualityReport = {
  image_id: string;
  view: string;
  overall_pass: boolean;
  blur_score: number;
  exposure_score: number;
  overexposed_frac: number;
  distance_ok: boolean;
  angle_ok: boolean;
  scalp_visibility: number | null;
  reasons: string[];
  retake_guidance: string[];
  /** Framing similarity to the previous scan's same view. null = no reference. */
  framing_match: number | null;
  confidence: Confidence;
  is_mock: boolean;
};

export type CaptureReference = {
  session_id: string;
  created_at: string;
  views: string[];
} | null;

export type Observation = {
  kind: string;
  value_num: number | null;
  value_label: string | null;
  unit: string | null;
  confidence: number;
  confidence_basis: string;
  model_name: string;
  model_version: string;
  is_mock: boolean;
  /** False for mock heuristics AND for real models that have not passed the
   *  stratified fairness evaluation. Warn on either. */
  validated: boolean;
  observation_type: "visual_observation" | "ai_inference";
};

/** How an observation's trustworthiness should be labelled. */
export function modelTrustLabel(o: Pick<Observation, "is_mock" | "validated">):
  | { variant: "mock"; text: string }
  | null {
  if (o.is_mock) return { variant: "mock", text: "mock · not validated" };
  if (!o.validated) return { variant: "mock", text: "unvalidated model" };
  return null;
}

export type EvidenceRef = {
  id: string;
  source: string;
  title: string;
  url: string;
  publisher: string;
  evidence_grade: string;
};

export type Recommendation = {
  type: string;
  title: string;
  body: string;
  confidence: number;
  requires_clinician: boolean;
  is_prescription: boolean;
  evidence: EvidenceRef[];
};

export type Analysis = {
  session_id: string;
  domain: string;
  status: string;
  overall_confidence: number;
  skin_appearance_index: number | null;
  hair_summary: Record<string, { value: number | null; label: string | null; confidence: number } | null> | null;
  observations: Observation[];
  safety_verdict: {
    verdict: "ok" | "caution" | "refer";
    red_flags: string[];
    suppressed_cosmetic: boolean;
    message: string;
  } | null;
  recommendations: Recommendation[];
  explanation: {
    observation?: string;
    reasoning?: string;
    confidence?: Confidence;
    evidence?: EvidenceRef[];
    limitations?: string[];
    summary?: string;
  } | null;
  disclaimers: string[];
};

const TOKEN_KEY = "hairgpt.access";
const REFRESH_KEY = "hairgpt.refresh";

export function getToken() {
  if (typeof window === "undefined") return null;
  return localStorage.getItem(TOKEN_KEY);
}
export function setTokens(access: string, refresh: string) {
  localStorage.setItem(TOKEN_KEY, access);
  localStorage.setItem(REFRESH_KEY, refresh);
}
export function clearTokens() {
  localStorage.removeItem(TOKEN_KEY);
  localStorage.removeItem(REFRESH_KEY);
}

/** Turn FastAPI's error shapes into something a person can act on. */
function describeDetail(detail: unknown, status: number): string {
  if (typeof detail === "string") return detail;
  // Pydantic validation errors: [{loc, msg, ...}]
  if (Array.isArray(detail)) {
    const parts = detail
      .map((d: any) => {
        const field = Array.isArray(d?.loc) ? d.loc[d.loc.length - 1] : null;
        const msg = d?.msg ?? "is invalid";
        return field ? `${field}: ${msg}` : msg;
      })
      .filter(Boolean);
    if (parts.length) return parts.join("; ");
  }
  if (detail && typeof detail === "object") {
    const d = detail as any;
    if (d.code === "consent_required") return "Consent is required before analysis.";
    if (d.code === "views_incomplete")
      return `Views still needed: ${(d.missing_or_failed ?? []).join(", ")}`;
    if (d.message) return String(d.message);
  }
  return `Request failed (${status})`;
}

export class ApiError extends Error {
  constructor(public status: number, public detail: unknown) {
    super(describeDetail(detail, status));
  }
}

async function request<T>(path: string, init: RequestInit = {}): Promise<T> {
  const token = getToken();
  const headers = new Headers(init.headers);
  if (token) headers.set("Authorization", `Bearer ${token}`);
  if (!(init.body instanceof FormData) && init.body) headers.set("Content-Type", "application/json");

  const res = await fetch(`/api/v1${path}`, { ...init, headers });
  if (res.status === 204) return undefined as T;
  const text = await res.text();
  const data = text ? JSON.parse(text) : null;
  if (!res.ok) throw new ApiError(res.status, data?.detail ?? data);
  return data as T;
}

export const api = {
  // Auth
  register: (body: { email: string; password: string; display_name?: string }) =>
    request("/auth/register", { method: "POST", body: JSON.stringify(body) }),
  login: async (email: string, password: string) => {
    const r = await request<{ access_token: string; refresh_token: string }>("/auth/login", {
      method: "POST",
      body: JSON.stringify({ email, password }),
    });
    setTokens(r.access_token, r.refresh_token);
    return r;
  },
  me: () => request<{ user: any; consents: any[] }>("/auth/me"),
  setConsent: (purpose: string, granted: boolean) =>
    request("/auth/consents", { method: "POST", body: JSON.stringify({ purpose, granted }) }),

  // Scans
  captureReference: (domain: "hair" | "skin") =>
    request<{ reference: CaptureReference }>(`/scans/reference?domain=${domain}`),
  createScan: (domain: "hair" | "skin") =>
    request<{ session_id: string; domain: string; required_views: string[]; status: string }>("/scans", {
      method: "POST",
      body: JSON.stringify({ domain }),
    }),
  uploadImage: (sessionId: string, view: string, file: Blob) => {
    const fd = new FormData();
    fd.append("view", view);
    fd.append("file", file, `${view}.jpg`);
    return request<QualityReport>(`/scans/${sessionId}/images/upload`, { method: "POST", body: fd });
  },
  analyze: (sessionId: string, symptoms?: Record<string, unknown>) =>
    request<{ status: string }>(`/scans/${sessionId}/analyze`, {
      method: "POST",
      body: JSON.stringify(symptoms ?? {}),
    }),
  result: (sessionId: string) => request<Analysis>(`/scans/${sessionId}/result`),
  listScans: () => request<any[]>("/scans"),
  doctorReport: (sessionId: string) => request<any>(`/scans/${sessionId}/doctor-report`),

  // Timeline / compare
  timeline: () => request<any>("/timeline"),
  compare: (before: string, after: string) =>
    request<any>("/comparisons", { method: "POST", body: JSON.stringify({ session_before: before, session_after: after }) }),

  // Treatments
  listTreatments: () => request<any[]>("/treatments"),
  createTreatment: (body: any) => request<any>("/treatments", { method: "POST", body: JSON.stringify(body) }),
  deleteTreatment: (id: string) => request<void>(`/treatments/${id}`, { method: "DELETE" }),
  logAdherence: (id: string, taken: boolean) =>
    request<any>(`/treatments/${id}/adherence`, { method: "POST", body: JSON.stringify({ taken }) }),
  adherenceSummary: () => request<any[]>("/treatments/adherence/summary"),

  // Products
  recommendProducts: (body: any) => request<any>("/products/recommend", { method: "POST", body: JSON.stringify(body) }),
  listProducts: () => request<any[]>("/products"),

  // Clinical history
  getHistory: () => request<ClinicalHistory | null>("/history"),
  saveHistory: (body: Partial<ClinicalHistory>) =>
    request<ClinicalHistory>("/history", { method: "PUT", body: JSON.stringify(body) }),

  // Shedding
  listShedding: (days = 90) => request<SheddingEntry[]>(`/shedding?days=${days}`),
  logShedding: (body: Partial<SheddingEntry>) =>
    request<SheddingEntry>("/shedding", { method: "POST", body: JSON.stringify(body) }),
  sheddingTrend: (windowDays = 60) => request<SheddingTrend>(`/shedding/trend?window_days=${windowDays}`),
};

export type ClinicalHistory = {
  id?: string;
  onset: string | null;
  duration_months: number | null;
  pattern: string | null;
  family_history_hair_loss: boolean;
  family_history_side: string | null;
  thyroid_condition: boolean;
  iron_deficiency: boolean;
  autoimmune_condition: boolean;
  pcos: boolean;
  scalp_condition: boolean;
  recent_illness: boolean;
  recent_surgery: boolean;
  major_stress: boolean;
  rapid_weight_loss: boolean;
  postpartum: boolean;
  trigger_months_ago: number | null;
  medications: string[];
  tight_hairstyles: boolean;
  chemical_treatments: boolean;
  heat_styling: boolean;
  scalp_itch: boolean;
  scalp_pain: boolean;
  body_hair_change: boolean;
  menstrual_irregularity: boolean;
  notes: string | null;
  flagged_medications?: string[];
};

export type SheddingEntry = {
  id?: string;
  date?: string;
  count: number | null;
  bucket: string | null;
  context: string;
  washed_hair: boolean;
  note: string | null;
};

export type SheddingTrend = {
  window_days: number;
  entries: number;
  average_by_context: Record<string, number>;
  trend: "increasing" | "stable" | "decreasing" | "insufficient_data";
  trend_note: string;
  disclaimer: string;
};

export const EMPTY_HISTORY: ClinicalHistory = {
  onset: null,
  duration_months: null,
  pattern: null,
  family_history_hair_loss: false,
  family_history_side: null,
  thyroid_condition: false,
  iron_deficiency: false,
  autoimmune_condition: false,
  pcos: false,
  scalp_condition: false,
  recent_illness: false,
  recent_surgery: false,
  major_stress: false,
  rapid_weight_loss: false,
  postpartum: false,
  trigger_months_ago: null,
  medications: [],
  tight_hairstyles: false,
  chemical_treatments: false,
  heat_styling: false,
  scalp_itch: false,
  scalp_pain: false,
  body_hair_change: false,
  menstrual_irregularity: false,
  notes: null,
};
