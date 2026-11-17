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

export interface CustomBody {
  name: string;
  description: string;
  duration_weeks: number;
  roles: Pick<Role, "skill" | "min_level" | "hours_per_week" | "critical">[];
  extra_members: Profile[];
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

export interface SquadsResponse {
  project: Project;
  squads: Record<Squad["profile"], Squad>;
}

export interface Meta {
  skills: Record<string, string>;
  levels: Record<string, string>;
}

export interface Question {
  id: string;
  type: "multi" | "levels" | "choice" | "open";
  text: string;
  max?: number;
  optional?: boolean;
  options?: { value: string | number; label: string }[];
}

export interface Profile {
  name: string;
  months_in_citi: number;
  skills: Record<string, number>;
  learning_goals: string[];
}
