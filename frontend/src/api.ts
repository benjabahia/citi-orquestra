import type { ChatMessage, CoherenceWarning, CustomBody, DraftSkill, ImportResult, Meta, Mode, Profile, Project, Question, Role, Squad, SquadsResponse, StressResponse, SummaryBody, Substitute, TeamMember } from "./types";

async function call<T>(path: string, body?: unknown, timeoutMs = 25000): Promise<T> {
  // Se o servidor não responder a tempo (padrão: 25 s), avisa em vez de deixar a tela esperando para sempre.
  const control = new AbortController();
  const timer = setTimeout(() => control.abort(), timeoutMs);
  let response: Response;
  try {
    response = await fetch(path, {
      method: body === undefined ? "GET" : "POST",
      headers: body === undefined ? undefined : { "Content-Type": "application/json" },
      body: body === undefined ? undefined : JSON.stringify(body),
      signal: control.signal,
    });
  } catch {
    throw new Error("O servidor não respondeu. Confira se o terminal com o servidor continua aberto e tente de novo.");
  } finally {
    clearTimeout(timer);
  }
  if (!response.ok) {
    let detail = "Algo deu errado. Tente de novo.";
    try {
      const data = await response.json();
      if (typeof data.detail === "string") detail = data.detail;
      else if (Array.isArray(data.detail)) detail = "Confira os campos preenchidos.";
    } catch {
      /* mantém a mensagem padrão */
    }
    throw new Error(detail);
  }
  return response.json() as Promise<T>;
}

export const api = {
  meta: () => call<Meta>("/api/meta"),
  aiStatus: () => call<{ mode: Mode }>("/api/ai/status"),
  projects: () => call<Project[]>("/api/projects"),
  squads: (id: string) => call<SquadsResponse>(`/api/projects/${id}/squads`),
  parseBriefing: (text: string) =>
    call<{ name: string; duration_weeks: number; roles: Role[]; mode: Mode }>("/api/briefing/parse", { text }),
  buildCustom: (body: CustomBody) => call<SquadsResponse>("/api/squads/build", body),
  team: (body: CustomBody) => call<{ members: TeamMember[]; duration_weeks: number }>("/api/squads/team", body),
  whatIf: (projectId: string, body: { profile: string; assignments: (string | null)[]; role_index: number; custom: CustomBody | null }) =>
    call<{ current: Squad; substitutes: Substitute[] }>(`/api/projects/${projectId}/whatif`, body),
  stress: (projectId: string, body: { profile: string; assignments: (string | null)[]; custom: CustomBody | null }) =>
    call<StressResponse>(`/api/projects/${projectId}/stress`, body),
  apply: (
    projectId: string,
    body: { profile: string; assignments: (string | null)[]; role_index: number; custom: CustomBody | null; member_id: string | null },
  ) => call<{ squad: Squad }>(`/api/projects/${projectId}/apply`, body),
  summary: (body: SummaryBody) => call<{ text: string }>("/api/export/summary", body),
  importMembers: (text: string) => call<ImportResult>("/api/members/import", { text }),
  membersTemplate: () => call<{ csv: string }>("/api/members/template"),
  questions: () => call<{ questions: Question[] }>("/api/profile/questions"),
  interpret: (name: string, answers: unknown) =>
    call<{
      profile: Profile;
      suggested_skills: { skill: string; skill_label: string }[];
      summary: string;
      mode: Mode;
    }>("/api/profile/interpret", { name, answers }),
  interviewNext: (body: { name: string; months_in_citi: number; history: ChatMessage[] }) =>
    call<{ done: boolean; question: string | null; asked: number }>("/api/profile/interview/next", body, 40000),
  interviewPropose: (body: { name: string; months_in_citi: number; history: ChatMessage[] }) =>
    call<{ status: "ok" | "sem_evidencia"; message: string | null; skills: DraftSkill[]; warnings: CoherenceWarning[] }>(
      "/api/profile/interview/propose", body, 40000),
  interviewCheck: (body: { months_in_citi: number; skills: Record<string, number>; history: ChatMessage[] }) =>
    call<{ warnings: CoherenceWarning[] }>("/api/profile/interview/check", body),
};
