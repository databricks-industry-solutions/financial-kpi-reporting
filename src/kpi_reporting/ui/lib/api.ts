import { useQuery, useSuspenseQuery, useMutation } from "@tanstack/react-query";
import type { UseQueryOptions, UseSuspenseQueryOptions, UseMutationOptions } from "@tanstack/react-query";

export interface AiBiDashboardUrl {
  dashboard_id: string;
  url: string;
}

export interface ConfluencePublishResult {
  confluence_page_id: string;
  confluence_page_url: string;
}

export interface CurrentUser {
  department_id?: string | null;
  department_name?: string | null;
  email: string;
  is_executive?: boolean;
  job_name?: string | null;
  name: string;
  operation_unit_code?: string | null;
  role?: string;
}

export interface DashboardSummary {
  departments_reporting: number;
  filled_entries: number;
  gm_reviewed_entries: number;
  locked_entries: number;
  total_entries: number;
}

export interface DepartmentDetail {
  department: DepartmentOut;
  fill_rate: number;
  kpi_count: number;
  lock_rate: number;
  submissions: SubmissionOut[];
}

export interface DepartmentOut {
  created_at: string;
  id: string;
  lead_name: string;
  name: string;
}

export interface ForecastPoint {
  actual?: number | null;
  high?: number | null;
  is_forecast?: boolean;
  low?: number | null;
  mid?: number | null;
  period: string;
}

export interface ForecastResponse {
  forecasts: KpiForecast[];
}

export interface GenieAskRequest {
  content: string;
  conversation_id?: string | null;
}

export interface GenieAskResponse {
  attachments?: GenieAttachment[];
  conversation_id?: string | null;
  message_id?: string | null;
  status: string;
}

export interface GenieAttachment {
  columns?: string[];
  data_array?: unknown[];
  row_count?: number;
  sql?: string | null;
  text?: string | null;
  truncated?: boolean;
}

export interface GenieSpaceUrl {
  space_id: string;
  url: string;
}

export interface HTTPValidationError {
  detail?: ValidationError[];
}

export interface JustifyRequest {
  field: string;
  submission_id: string;
}

export interface KpiForecast {
  insight: string;
  kpi_name: string;
  kpi_unit: string;
  points: ForecastPoint[];
}

export interface NarrativeRequest {
  period: string;
}

export interface NarrativeResponse {
  narrative: string;
}

export interface PublishDashboardSummaryRequest {
  period?: string | null;
}

export interface PublishSubmissionsSummaryRequest {
  department_name: string;
  period?: string | null;
}

export interface RegionRiskSummary {
  headline?: string;
  kpi_sentiments?: Record<string, string>;
  overall_sentiment?: string;
  region_name?: string;
  risk_level?: string;
}

export interface RiskItem {
  affected_kpis?: string[];
  affected_regions?: string[];
  evidence?: string;
  rank?: number;
  recommended_action?: string;
  severity?: string;
  title?: string;
}

export interface RiskReport {
  cross_cutting_patterns: string;
  executive_summary: string;
  generated_at: string;
  outlook: string;
  period: string;
  region_summaries: RegionRiskSummary[];
  top_risks: RiskItem[];
}

export interface RiskReportRequest {
  period: string;
}

export interface SubmissionOut {
  confluence_page_id?: string | null;
  confluence_page_url?: string | null;
  department_id: string;
  department_name: string;
  expected_impact: string;
  external_factors: string;
  id: string;
  internal_factors: string;
  key_drivers_qualitative: string;
  key_drivers_quantitative: string;
  kpi_category: string;
  kpi_lockin: boolean;
  kpi_name: string;
  kpi_number: number;
  kpi_unit: string;
  kpi_value?: number | null;
  oneoff_events: string;
  period: string;
  period_end: string;
  period_start: string;
  planned_actions: string;
  reviewed_by_gm: string;
  sentiment_tags: string;
  submitted_at: string;
  submitted_by: string;
  updated_at: string;
}

export interface SubmissionUpdateRequest {
  expected_impact?: string | null;
  external_factors?: string | null;
  internal_factors?: string | null;
  key_drivers_qualitative?: string | null;
  key_drivers_quantitative?: string | null;
  kpi_lockin?: boolean | null;
  oneoff_events?: string | null;
  planned_actions?: string | null;
  reviewed_by_gm?: string | null;
  sentiment_tags?: string | null;
}

export interface TaskAction {
  label: string;
  route: string;
  variant?: string;
}

export interface TaskItem {
  actions?: TaskAction[];
  count?: number | null;
  description: string;
  id: string;
  negative_count?: number | null;
  period: string;
  route?: string | null;
  status: string;
  title: string;
  total?: number | null;
  unlocked_count?: number | null;
}

export interface TasksResponse {
  period: string;
  tasks: TaskItem[];
}

export interface ValidationError {
  ctx?: Record<string, unknown>;
  input?: unknown;
  loc: (string | number)[];
  msg: string;
  type: string;
}

export interface VersionOut {
  version: string;
}

export interface GetDepartmentDetailParams {
  dept_id: string;
  period?: string | null;
}

export interface GetDashboardSummaryParams {
  period?: string | null;
}

export interface GetSubmissionsParams {
  department_id?: string | null;
  period?: string | null;
}

export interface GetSubmissionParams {
  sub_id: string;
}

export interface UpdateSubmissionParams {
  sub_id: string;
}

export interface PublishToConfluenceParams {
  sub_id: string;
}

export interface GetTasksParams {
  persona: string;
  department_id?: string | null;
}

export class ApiError extends Error {
  status: number;
  statusText: string;
  body: unknown;

  constructor(status: number, statusText: string, body: unknown) {
    super(`HTTP ${status}: ${statusText}`);
    this.name = "ApiError";
    this.status = status;
    this.statusText = statusText;
    this.body = body;
  }
}

export const agentJustify = async (data: JustifyRequest, options?: RequestInit): Promise<{ data: unknown }> => {
  const res = await fetch("/api/agent/justify", { ...options, method: "POST", headers: { "Content-Type": "application/json", ...options?.headers }, body: JSON.stringify(data) });
  if (!res.ok) {
    const body = await res.text();
    let parsed: unknown;
    try { parsed = JSON.parse(body); } catch { parsed = body; }
    throw new ApiError(res.status, res.statusText, parsed);
  }
  return { data: await res.json() };
};

export function useAgentJustify(options?: { mutation?: UseMutationOptions<{ data: unknown }, ApiError, JustifyRequest> }) {
  return useMutation({ mutationFn: (data) => agentJustify(data), ...options?.mutation });
}

export const agentNarrative = async (data: NarrativeRequest, options?: RequestInit): Promise<{ data: NarrativeResponse }> => {
  const res = await fetch("/api/agent/narrative", { ...options, method: "POST", headers: { "Content-Type": "application/json", ...options?.headers }, body: JSON.stringify(data) });
  if (!res.ok) {
    const body = await res.text();
    let parsed: unknown;
    try { parsed = JSON.parse(body); } catch { parsed = body; }
    throw new ApiError(res.status, res.statusText, parsed);
  }
  return { data: await res.json() };
};

export function useAgentNarrative(options?: { mutation?: UseMutationOptions<{ data: NarrativeResponse }, ApiError, NarrativeRequest> }) {
  return useMutation({ mutationFn: (data) => agentNarrative(data), ...options?.mutation });
}

export const generateRiskReport = async (data: RiskReportRequest, options?: RequestInit): Promise<{ data: RiskReport }> => {
  const res = await fetch("/api/agent/risk-report", { ...options, method: "POST", headers: { "Content-Type": "application/json", ...options?.headers }, body: JSON.stringify(data) });
  if (!res.ok) {
    const body = await res.text();
    let parsed: unknown;
    try { parsed = JSON.parse(body); } catch { parsed = body; }
    throw new ApiError(res.status, res.statusText, parsed);
  }
  return { data: await res.json() };
};

export function useGenerateRiskReport(options?: { mutation?: UseMutationOptions<{ data: RiskReport }, ApiError, RiskReportRequest> }) {
  return useMutation({ mutationFn: (data) => generateRiskReport(data), ...options?.mutation });
}

export const publishRiskReport = async (data: RiskReport, options?: RequestInit): Promise<{ data: ConfluencePublishResult }> => {
  const res = await fetch("/api/agent/risk-report/publish-confluence", { ...options, method: "POST", headers: { "Content-Type": "application/json", ...options?.headers }, body: JSON.stringify(data) });
  if (!res.ok) {
    const body = await res.text();
    let parsed: unknown;
    try { parsed = JSON.parse(body); } catch { parsed = body; }
    throw new ApiError(res.status, res.statusText, parsed);
  }
  return { data: await res.json() };
};

export function usePublishRiskReport(options?: { mutation?: UseMutationOptions<{ data: ConfluencePublishResult }, ApiError, RiskReport> }) {
  return useMutation({ mutationFn: (data) => publishRiskReport(data), ...options?.mutation });
}

export const getAiBiDashboardUrl = async (options?: RequestInit): Promise<{ data: AiBiDashboardUrl }> => {
  const res = await fetch("/api/aibi/dashboard-url", { ...options, method: "GET" });
  if (!res.ok) {
    const body = await res.text();
    let parsed: unknown;
    try { parsed = JSON.parse(body); } catch { parsed = body; }
    throw new ApiError(res.status, res.statusText, parsed);
  }
  return { data: await res.json() };
};

export const getAiBiDashboardUrlKey = () => {
  return ["/api/aibi/dashboard-url"] as const;
};

export function useGetAiBiDashboardUrl<TData = { data: AiBiDashboardUrl }>(options?: { query?: Omit<UseQueryOptions<{ data: AiBiDashboardUrl }, ApiError, TData>, "queryKey" | "queryFn"> }) {
  return useQuery({ queryKey: getAiBiDashboardUrlKey(), queryFn: () => getAiBiDashboardUrl(), ...options?.query });
}

export function useGetAiBiDashboardUrlSuspense<TData = { data: AiBiDashboardUrl }>(options?: { query?: Omit<UseSuspenseQueryOptions<{ data: AiBiDashboardUrl }, ApiError, TData>, "queryKey" | "queryFn"> }) {
  return useSuspenseQuery({ queryKey: getAiBiDashboardUrlKey(), queryFn: () => getAiBiDashboardUrl(), ...options?.query });
}

export const getDepartmentDetail = async (params: GetDepartmentDetailParams, options?: RequestInit): Promise<{ data: DepartmentDetail }> => {
  const searchParams = new URLSearchParams();
  if (params?.period != null) searchParams.set("period", String(params?.period));
  const queryString = searchParams.toString();
  const url = queryString ? `/api/dashboard/department/${params.dept_id}?${queryString}` : `/api/dashboard/department/${params.dept_id}`;
  const res = await fetch(url, { ...options, method: "GET" });
  if (!res.ok) {
    const body = await res.text();
    let parsed: unknown;
    try { parsed = JSON.parse(body); } catch { parsed = body; }
    throw new ApiError(res.status, res.statusText, parsed);
  }
  return { data: await res.json() };
};

export const getDepartmentDetailKey = (params?: GetDepartmentDetailParams) => {
  return ["/api/dashboard/department/{dept_id}", params] as const;
};

export function useGetDepartmentDetail<TData = { data: DepartmentDetail }>(options: { params: GetDepartmentDetailParams; query?: Omit<UseQueryOptions<{ data: DepartmentDetail }, ApiError, TData>, "queryKey" | "queryFn"> }) {
  return useQuery({ queryKey: getDepartmentDetailKey(options.params), queryFn: () => getDepartmentDetail(options.params), ...options?.query });
}

export function useGetDepartmentDetailSuspense<TData = { data: DepartmentDetail }>(options: { params: GetDepartmentDetailParams; query?: Omit<UseSuspenseQueryOptions<{ data: DepartmentDetail }, ApiError, TData>, "queryKey" | "queryFn"> }) {
  return useSuspenseQuery({ queryKey: getDepartmentDetailKey(options.params), queryFn: () => getDepartmentDetail(options.params), ...options?.query });
}

export const getDashboardSummary = async (params?: GetDashboardSummaryParams, options?: RequestInit): Promise<{ data: DashboardSummary }> => {
  const searchParams = new URLSearchParams();
  if (params?.period != null) searchParams.set("period", String(params?.period));
  const queryString = searchParams.toString();
  const url = queryString ? `/api/dashboard/summary?${queryString}` : `/api/dashboard/summary`;
  const res = await fetch(url, { ...options, method: "GET" });
  if (!res.ok) {
    const body = await res.text();
    let parsed: unknown;
    try { parsed = JSON.parse(body); } catch { parsed = body; }
    throw new ApiError(res.status, res.statusText, parsed);
  }
  return { data: await res.json() };
};

export const getDashboardSummaryKey = (params?: GetDashboardSummaryParams) => {
  return ["/api/dashboard/summary", params] as const;
};

export function useGetDashboardSummary<TData = { data: DashboardSummary }>(options?: { params?: GetDashboardSummaryParams; query?: Omit<UseQueryOptions<{ data: DashboardSummary }, ApiError, TData>, "queryKey" | "queryFn"> }) {
  return useQuery({ queryKey: getDashboardSummaryKey(options?.params), queryFn: () => getDashboardSummary(options?.params), ...options?.query });
}

export function useGetDashboardSummarySuspense<TData = { data: DashboardSummary }>(options?: { params?: GetDashboardSummaryParams; query?: Omit<UseSuspenseQueryOptions<{ data: DashboardSummary }, ApiError, TData>, "queryKey" | "queryFn"> }) {
  return useSuspenseQuery({ queryKey: getDashboardSummaryKey(options?.params), queryFn: () => getDashboardSummary(options?.params), ...options?.query });
}

export const getDepartments = async (options?: RequestInit): Promise<{ data: DepartmentOut[] }> => {
  const res = await fetch("/api/departments", { ...options, method: "GET" });
  if (!res.ok) {
    const body = await res.text();
    let parsed: unknown;
    try { parsed = JSON.parse(body); } catch { parsed = body; }
    throw new ApiError(res.status, res.statusText, parsed);
  }
  return { data: await res.json() };
};

export const getDepartmentsKey = () => {
  return ["/api/departments"] as const;
};

export function useGetDepartments<TData = { data: DepartmentOut[] }>(options?: { query?: Omit<UseQueryOptions<{ data: DepartmentOut[] }, ApiError, TData>, "queryKey" | "queryFn"> }) {
  return useQuery({ queryKey: getDepartmentsKey(), queryFn: () => getDepartments(), ...options?.query });
}

export function useGetDepartmentsSuspense<TData = { data: DepartmentOut[] }>(options?: { query?: Omit<UseSuspenseQueryOptions<{ data: DepartmentOut[] }, ApiError, TData>, "queryKey" | "queryFn"> }) {
  return useSuspenseQuery({ queryKey: getDepartmentsKey(), queryFn: () => getDepartments(), ...options?.query });
}

export const getKpiForecast = async (options?: RequestInit): Promise<{ data: ForecastResponse }> => {
  const res = await fetch("/api/forecast/kpi", { ...options, method: "GET" });
  if (!res.ok) {
    const body = await res.text();
    let parsed: unknown;
    try { parsed = JSON.parse(body); } catch { parsed = body; }
    throw new ApiError(res.status, res.statusText, parsed);
  }
  return { data: await res.json() };
};

export const getKpiForecastKey = () => {
  return ["/api/forecast/kpi"] as const;
};

export function useGetKpiForecast<TData = { data: ForecastResponse }>(options?: { query?: Omit<UseQueryOptions<{ data: ForecastResponse }, ApiError, TData>, "queryKey" | "queryFn"> }) {
  return useQuery({ queryKey: getKpiForecastKey(), queryFn: () => getKpiForecast(), ...options?.query });
}

export function useGetKpiForecastSuspense<TData = { data: ForecastResponse }>(options?: { query?: Omit<UseSuspenseQueryOptions<{ data: ForecastResponse }, ApiError, TData>, "queryKey" | "queryFn"> }) {
  return useSuspenseQuery({ queryKey: getKpiForecastKey(), queryFn: () => getKpiForecast(), ...options?.query });
}

export const genieAsk = async (data: GenieAskRequest, options?: RequestInit): Promise<{ data: GenieAskResponse }> => {
  const res = await fetch("/api/genie/ask", { ...options, method: "POST", headers: { "Content-Type": "application/json", ...options?.headers }, body: JSON.stringify(data) });
  if (!res.ok) {
    const body = await res.text();
    let parsed: unknown;
    try { parsed = JSON.parse(body); } catch { parsed = body; }
    throw new ApiError(res.status, res.statusText, parsed);
  }
  return { data: await res.json() };
};

export function useGenieAsk(options?: { mutation?: UseMutationOptions<{ data: GenieAskResponse }, ApiError, GenieAskRequest> }) {
  return useMutation({ mutationFn: (data) => genieAsk(data), ...options?.mutation });
}

export const getGenieSpaceUrl = async (options?: RequestInit): Promise<{ data: GenieSpaceUrl }> => {
  const res = await fetch("/api/genie/space-url", { ...options, method: "GET" });
  if (!res.ok) {
    const body = await res.text();
    let parsed: unknown;
    try { parsed = JSON.parse(body); } catch { parsed = body; }
    throw new ApiError(res.status, res.statusText, parsed);
  }
  return { data: await res.json() };
};

export const getGenieSpaceUrlKey = () => {
  return ["/api/genie/space-url"] as const;
};

export function useGetGenieSpaceUrl<TData = { data: GenieSpaceUrl }>(options?: { query?: Omit<UseQueryOptions<{ data: GenieSpaceUrl }, ApiError, TData>, "queryKey" | "queryFn"> }) {
  return useQuery({ queryKey: getGenieSpaceUrlKey(), queryFn: () => getGenieSpaceUrl(), ...options?.query });
}

export function useGetGenieSpaceUrlSuspense<TData = { data: GenieSpaceUrl }>(options?: { query?: Omit<UseSuspenseQueryOptions<{ data: GenieSpaceUrl }, ApiError, TData>, "queryKey" | "queryFn"> }) {
  return useSuspenseQuery({ queryKey: getGenieSpaceUrlKey(), queryFn: () => getGenieSpaceUrl(), ...options?.query });
}

export const getCurrentUser = async (options?: RequestInit): Promise<{ data: CurrentUser }> => {
  const res = await fetch("/api/me", { ...options, method: "GET" });
  if (!res.ok) {
    const body = await res.text();
    let parsed: unknown;
    try { parsed = JSON.parse(body); } catch { parsed = body; }
    throw new ApiError(res.status, res.statusText, parsed);
  }
  return { data: await res.json() };
};

export const getCurrentUserKey = () => {
  return ["/api/me"] as const;
};

export function useGetCurrentUser<TData = { data: CurrentUser }>(options?: { query?: Omit<UseQueryOptions<{ data: CurrentUser }, ApiError, TData>, "queryKey" | "queryFn"> }) {
  return useQuery({ queryKey: getCurrentUserKey(), queryFn: () => getCurrentUser(), ...options?.query });
}

export function useGetCurrentUserSuspense<TData = { data: CurrentUser }>(options?: { query?: Omit<UseSuspenseQueryOptions<{ data: CurrentUser }, ApiError, TData>, "queryKey" | "queryFn"> }) {
  return useSuspenseQuery({ queryKey: getCurrentUserKey(), queryFn: () => getCurrentUser(), ...options?.query });
}

export const publishDashboardSummary = async (data: PublishDashboardSummaryRequest, options?: RequestInit): Promise<{ data: ConfluencePublishResult }> => {
  const res = await fetch("/api/publish-dashboard-summary", { ...options, method: "POST", headers: { "Content-Type": "application/json", ...options?.headers }, body: JSON.stringify(data) });
  if (!res.ok) {
    const body = await res.text();
    let parsed: unknown;
    try { parsed = JSON.parse(body); } catch { parsed = body; }
    throw new ApiError(res.status, res.statusText, parsed);
  }
  return { data: await res.json() };
};

export function usePublishDashboardSummary(options?: { mutation?: UseMutationOptions<{ data: ConfluencePublishResult }, ApiError, PublishDashboardSummaryRequest> }) {
  return useMutation({ mutationFn: (data) => publishDashboardSummary(data), ...options?.mutation });
}

export const publishSubmissionsSummary = async (data: PublishSubmissionsSummaryRequest, options?: RequestInit): Promise<{ data: ConfluencePublishResult }> => {
  const res = await fetch("/api/publish-submissions-summary", { ...options, method: "POST", headers: { "Content-Type": "application/json", ...options?.headers }, body: JSON.stringify(data) });
  if (!res.ok) {
    const body = await res.text();
    let parsed: unknown;
    try { parsed = JSON.parse(body); } catch { parsed = body; }
    throw new ApiError(res.status, res.statusText, parsed);
  }
  return { data: await res.json() };
};

export function usePublishSubmissionsSummary(options?: { mutation?: UseMutationOptions<{ data: ConfluencePublishResult }, ApiError, PublishSubmissionsSummaryRequest> }) {
  return useMutation({ mutationFn: (data) => publishSubmissionsSummary(data), ...options?.mutation });
}

export const getSubmissions = async (params?: GetSubmissionsParams, options?: RequestInit): Promise<{ data: SubmissionOut[] }> => {
  const searchParams = new URLSearchParams();
  if (params?.department_id != null) searchParams.set("department_id", String(params?.department_id));
  if (params?.period != null) searchParams.set("period", String(params?.period));
  const queryString = searchParams.toString();
  const url = queryString ? `/api/submissions?${queryString}` : `/api/submissions`;
  const res = await fetch(url, { ...options, method: "GET" });
  if (!res.ok) {
    const body = await res.text();
    let parsed: unknown;
    try { parsed = JSON.parse(body); } catch { parsed = body; }
    throw new ApiError(res.status, res.statusText, parsed);
  }
  return { data: await res.json() };
};

export const getSubmissionsKey = (params?: GetSubmissionsParams) => {
  return ["/api/submissions", params] as const;
};

export function useGetSubmissions<TData = { data: SubmissionOut[] }>(options?: { params?: GetSubmissionsParams; query?: Omit<UseQueryOptions<{ data: SubmissionOut[] }, ApiError, TData>, "queryKey" | "queryFn"> }) {
  return useQuery({ queryKey: getSubmissionsKey(options?.params), queryFn: () => getSubmissions(options?.params), ...options?.query });
}

export function useGetSubmissionsSuspense<TData = { data: SubmissionOut[] }>(options?: { params?: GetSubmissionsParams; query?: Omit<UseSuspenseQueryOptions<{ data: SubmissionOut[] }, ApiError, TData>, "queryKey" | "queryFn"> }) {
  return useSuspenseQuery({ queryKey: getSubmissionsKey(options?.params), queryFn: () => getSubmissions(options?.params), ...options?.query });
}

export const getSubmission = async (params: GetSubmissionParams, options?: RequestInit): Promise<{ data: SubmissionOut }> => {
  const res = await fetch(`/api/submissions/${params.sub_id}`, { ...options, method: "GET" });
  if (!res.ok) {
    const body = await res.text();
    let parsed: unknown;
    try { parsed = JSON.parse(body); } catch { parsed = body; }
    throw new ApiError(res.status, res.statusText, parsed);
  }
  return { data: await res.json() };
};

export const getSubmissionKey = (params?: GetSubmissionParams) => {
  return ["/api/submissions/{sub_id}", params] as const;
};

export function useGetSubmission<TData = { data: SubmissionOut }>(options: { params: GetSubmissionParams; query?: Omit<UseQueryOptions<{ data: SubmissionOut }, ApiError, TData>, "queryKey" | "queryFn"> }) {
  return useQuery({ queryKey: getSubmissionKey(options.params), queryFn: () => getSubmission(options.params), ...options?.query });
}

export function useGetSubmissionSuspense<TData = { data: SubmissionOut }>(options: { params: GetSubmissionParams; query?: Omit<UseSuspenseQueryOptions<{ data: SubmissionOut }, ApiError, TData>, "queryKey" | "queryFn"> }) {
  return useSuspenseQuery({ queryKey: getSubmissionKey(options.params), queryFn: () => getSubmission(options.params), ...options?.query });
}

export const updateSubmission = async (params: UpdateSubmissionParams, data: SubmissionUpdateRequest, options?: RequestInit): Promise<{ data: SubmissionOut }> => {
  const res = await fetch(`/api/submissions/${params.sub_id}`, { ...options, method: "PUT", headers: { "Content-Type": "application/json", ...options?.headers }, body: JSON.stringify(data) });
  if (!res.ok) {
    const body = await res.text();
    let parsed: unknown;
    try { parsed = JSON.parse(body); } catch { parsed = body; }
    throw new ApiError(res.status, res.statusText, parsed);
  }
  return { data: await res.json() };
};

export function useUpdateSubmission(options?: { mutation?: UseMutationOptions<{ data: SubmissionOut }, ApiError, { params: UpdateSubmissionParams; data: SubmissionUpdateRequest }> }) {
  return useMutation({ mutationFn: (vars) => updateSubmission(vars.params, vars.data), ...options?.mutation });
}

export const publishToConfluence = async (params: PublishToConfluenceParams, options?: RequestInit): Promise<{ data: ConfluencePublishResult }> => {
  const res = await fetch(`/api/submissions/${params.sub_id}/publish-confluence`, { ...options, method: "POST" });
  if (!res.ok) {
    const body = await res.text();
    let parsed: unknown;
    try { parsed = JSON.parse(body); } catch { parsed = body; }
    throw new ApiError(res.status, res.statusText, parsed);
  }
  return { data: await res.json() };
};

export function usePublishToConfluence(options?: { mutation?: UseMutationOptions<{ data: ConfluencePublishResult }, ApiError, { params: PublishToConfluenceParams }> }) {
  return useMutation({ mutationFn: (vars) => publishToConfluence(vars.params), ...options?.mutation });
}

export const getTasks = async (params: GetTasksParams, options?: RequestInit): Promise<{ data: TasksResponse }> => {
  const searchParams = new URLSearchParams();
  if (params.persona != null) searchParams.set("persona", String(params.persona));
  if (params?.department_id != null) searchParams.set("department_id", String(params?.department_id));
  const queryString = searchParams.toString();
  const url = queryString ? `/api/tasks?${queryString}` : `/api/tasks`;
  const res = await fetch(url, { ...options, method: "GET" });
  if (!res.ok) {
    const body = await res.text();
    let parsed: unknown;
    try { parsed = JSON.parse(body); } catch { parsed = body; }
    throw new ApiError(res.status, res.statusText, parsed);
  }
  return { data: await res.json() };
};

export const getTasksKey = (params?: GetTasksParams) => {
  return ["/api/tasks", params] as const;
};

export function useGetTasks<TData = { data: TasksResponse }>(options: { params: GetTasksParams; query?: Omit<UseQueryOptions<{ data: TasksResponse }, ApiError, TData>, "queryKey" | "queryFn"> }) {
  return useQuery({ queryKey: getTasksKey(options.params), queryFn: () => getTasks(options.params), ...options?.query });
}

export function useGetTasksSuspense<TData = { data: TasksResponse }>(options: { params: GetTasksParams; query?: Omit<UseSuspenseQueryOptions<{ data: TasksResponse }, ApiError, TData>, "queryKey" | "queryFn"> }) {
  return useSuspenseQuery({ queryKey: getTasksKey(options.params), queryFn: () => getTasks(options.params), ...options?.query });
}

export const version = async (options?: RequestInit): Promise<{ data: VersionOut }> => {
  const res = await fetch("/api/version", { ...options, method: "GET" });
  if (!res.ok) {
    const body = await res.text();
    let parsed: unknown;
    try { parsed = JSON.parse(body); } catch { parsed = body; }
    throw new ApiError(res.status, res.statusText, parsed);
  }
  return { data: await res.json() };
};

export const versionKey = () => {
  return ["/api/version"] as const;
};

export function useVersion<TData = { data: VersionOut }>(options?: { query?: Omit<UseQueryOptions<{ data: VersionOut }, ApiError, TData>, "queryKey" | "queryFn"> }) {
  return useQuery({ queryKey: versionKey(), queryFn: () => version(), ...options?.query });
}

export function useVersionSuspense<TData = { data: VersionOut }>(options?: { query?: Omit<UseSuspenseQueryOptions<{ data: VersionOut }, ApiError, TData>, "queryKey" | "queryFn"> }) {
  return useSuspenseQuery({ queryKey: versionKey(), queryFn: () => version(), ...options?.query });
}

