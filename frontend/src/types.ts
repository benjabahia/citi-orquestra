export type Mode = "ia_real" | "simulado";

export interface Role {
  index?: number;
  skill: string;
  skill_label: string;
  min_level: number;
  hours_per_week: number;
  critical: boolean;
  reason?: string;
}

export interface Slot extends Role {
  member_id: string | null;
  member_name: string | null;
  member_level: number | null;
  is_novato: boolean;
}

export interface Factor {
  kind: string;
  points: number;
  message: string;
}

export interface Load {
  member_id: string;
  role_index: number;
  capacity: number;
  demand: number;
  mentoring_hours: number;
}

export interface Substitute {
  member_id: string;
  name: string;
  skill_level: number;
  is_novato: boolean;
  months_in_citi: number;
  metrics: Metrics;
  delta_entrega: number;
  delta_crescimento: number;
  delta_risco: number;
  new_issues: string[];
  resolved_issues: string[];
}

export interface StressRow {
  member_id: string;
  name: string;
  role_index: number;
  skill_label: string;
  critical: boolean;
  risco_before: number;
  risco_after: number;
  delta_risco: number;
  delta_entrega: number;
  entrega_after: number;
  main_issue: string | null;
}

export interface StressResponse {
  results: StressRow[];
  weakest_sentence: string;
}

export interface CustomBody {
  name: string;
  description: string;
  duration_weeks: number;
  roles: Pick<Role, "skill" | "min_level" | "hours_per_week" | "critical">[];
  extra_members: Profile[];
  replace_members?: Profile[] | null;
  /** Ajuste do gerente: id do membro -> horas livres e semanas fora. */
  availability?: Record<string, Hours>;
}

export interface Hours {
  weekly_hours: number;
  unavailable_weeks: number;
}

export interface TeamMember extends Hours {
  id: string;
  name: string;
  source: "planilha" | "perfil" | "exemplo";
  is_novato: boolean;
  available_hours: number;
}

export interface ImportError {
  line: number | null;
  column: string | null;
  message: string;
}

export interface ImportResult {
  ok: boolean;
  members: Profile[];
  errors: ImportError[];
  more_errors: number;
}

export interface Metrics {
  entrega: number;
  crescimento: number;
  risco: number;
  role_coverage: number[];
  factors: Factor[];
  loads: Load[];
  mentorships: { mentor_id: string; mentee_id: string; skill: string }[];
}

export interface Squad {
  profile: "segura" | "evolutiva" | "balanceada";
  slots: Slot[];
  assignments: (string | null)[];
  metrics: Metrics;
  notes: string[];
}

export interface Project {
  id: string;
  name: string;
  description: string;
  duration_weeks: number;
  roles: Role[];
}

export type Priority = "prazo" | "formar" | "equilibrio";

export interface Recommendation {
  priority: Priority;
  profile: Squad["profile"];
  reason: string;
  scores: Partial<Record<Squad["profile"], number>>;
}

export interface SquadsResponse {
  project: Project;
  squads: Record<Squad["profile"], Squad>;
  recommendations: Record<Priority, Recommendation>;
}

export interface Meta {
  skills: Record<string, string>;
  levels: Record<string, string>;
}

export interface Question {
  id: string;
  type: "multi" | "levels" | "choice" | "open" | "number";
  text: string;
  min?: number;
  max?: number;
  step?: number;
  unit?: string;
  suggestions?: number[];
  default?: number;
  optional?: boolean;
  options?: { value: string | number; label: string }[];
}

export interface Profile {
  name: string;
  months_in_citi: number;
  skills: Record<string, number>;
  learning_goals: string[];
  /** Perfis antigos não têm estes campos: o servidor usa 8 h e 0 semanas. */
  weekly_hours?: number;
  unavailable_weeks?: number;
}

export interface ChatMessage {
  role: "user" | "assistant";
  text: string;
}

export interface DraftSkill {
  skill: string;
  skill_label: string;
  level: number;
  anchor: string;
  evidence: string;
}

export interface CoherenceWarning {
  kind: "muitos_4" | "sem_evidencia" | "novato_alto" | "afirmacao_ampla";
  skill: string | null;
  message: string;
}

export interface SummaryBody {
  project_id: string;
  profile: string;
  assignments: (string | null)[];
  custom: CustomBody | null;
  /** true quando o teste de estresse já foi feito: o resumo inclui o ponto mais frágil. */
  include_weakest: boolean;
}
