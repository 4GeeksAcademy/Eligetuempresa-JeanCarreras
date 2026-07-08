export type ToastTone = "success" | "error" | "info";

export type CandidateRecord = {
  id: string;
  full_name: string;
  email: string;
  phone: string;
  position: string;
  linkedin_url: string | null;
  cv_url: string | null;
  status: string;
  stage: string;
  experience_years: number;
  notes_count: number;
  applied_at: string;
  updated_at: string;
};

export type CandidateApiRecord = Omit<CandidateRecord, "notes_count"> & {
  notes_count?: number;
  notes?: Array<{ id: string }>;
};

export type RecordCreatePayload = {
  full_name: string;
  email: string;
  phone: string;
  position: string;
  linkedin_url: string | null;
  cv_url: string | null;
  experience_years: number;
};

export type RecordsApiResponse = {
  total?: number;
  page?: number;
  limit?: number;
  data?: CandidateApiRecord[];
};

export type Note = {
  id: string;
  record_id: string;
  content: string;
  created_at: string;
};

export const STATUS_OPTIONS = ["new", "in_progress", "on_hold", "closed"];
export const STAGE_OPTIONS = [
  "sourced",
  "review",
  "screening",
  "interview",
  "assessment",
  "offer",
  "hired",
  "rejected",
];

export const STATUS_LABELS: Record<string, string> = {
  new: "Nueva",
  in_progress: "En proceso",
  on_hold: "En espera",
  closed: "Cerrada",
};

export const STAGE_LABELS: Record<string, string> = {
  sourced: "Captacion",
  review: "Revision inicial",
  screening: "Filtro de perfil",
  interview: "Entrevista",
  assessment: "Prueba operativa",
  offer: "Oferta",
  hired: "Contratado",
  rejected: "No continua",
};

export const DEFAULT_STATUSES = ["new", "in_progress", "on_hold", "closed"];
export const DEFAULT_STAGES = [
  "sourced",
  "review",
  "screening",
  "interview",
  "assessment",
  "offer",
  "hired",
  "rejected",
];

export const EMPTY_CREATE_FORM: RecordCreatePayload = {
  full_name: "",
  email: "",
  phone: "",
  position: "",
  linkedin_url: null,
  cv_url: null,
  experience_years: 0,
};
