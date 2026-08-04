from datetime import datetime
from pydantic import BaseModel
from .. import __version__


class VersionOut(BaseModel):
    version: str

    @classmethod
    def from_metadata(cls):
        return cls(version=__version__)


# --- Current User ---

class CurrentUser(BaseModel):
    email: str
    name: str
    department_name: str | None = None
    department_id: str | None = None
    operation_unit_code: str | None = None
    job_name: str | None = None
    role: str = "viewer"  # "gm", "blm", "bc", "executive", "viewer"
    is_executive: bool = False


# --- Tasks ---

# --- Risk Report ---

class RiskItem(BaseModel):
    model_config = {"extra": "ignore"}
    rank: int = 1
    title: str = ""
    severity: str = "medium"    # "high" | "medium" | "low"
    affected_regions: list[str] = []
    affected_kpis: list[str] = []
    evidence: str = ""          # 1-2 sentences from the actual data
    recommended_action: str = ""

class RegionRiskSummary(BaseModel):
    model_config = {"extra": "ignore"}
    region_name: str = ""
    overall_sentiment: str = "neutral"   # "positive" | "neutral" | "cautious" | "negative"
    risk_level: str = "none"             # "high" | "medium" | "low" | "none"
    headline: str = ""                   # one sentence
    kpi_sentiments: dict[str, str] = {}  # {kpi_name: sentiment}

class RiskReport(BaseModel):
    period: str
    generated_at: str
    executive_summary: str
    top_risks: list[RiskItem]
    region_summaries: list[RegionRiskSummary]
    cross_cutting_patterns: str
    outlook: str


class TaskAction(BaseModel):
    label: str
    route: str
    variant: str = "default"  # "default" | "destructive" | "outline"


class TaskItem(BaseModel):
    id: str
    title: str
    description: str
    period: str
    status: str  # "pending" | "in_progress" | "done"
    count: int | None = None          # generic count (GM: unjustified KPIs)
    total: int | None = None
    unlocked_count: int | None = None  # CFO: submissions not yet locked
    negative_count: int | None = None  # CFO: submissions with cautious/negative sentiment
    route: str | None = None           # primary deep-link route
    actions: list[TaskAction] = []     # labelled action buttons


class TasksResponse(BaseModel):
    tasks: list[TaskItem]
    period: str  # most relevant period


# --- Departments ---

class DepartmentOut(BaseModel):
    id: str
    name: str
    lead_name: str
    created_at: str


# --- KPI Submissions ---

class SubmissionOut(BaseModel):
    id: str
    department_id: str
    department_name: str
    kpi_name: str
    kpi_number: int
    kpi_category: str
    period: str
    period_start: str
    period_end: str
    kpi_value: float | None = None
    kpi_unit: str
    key_drivers_quantitative: str
    key_drivers_qualitative: str
    internal_factors: str
    external_factors: str
    oneoff_events: str
    planned_actions: str
    expected_impact: str
    sentiment_tags: str
    kpi_lockin: bool
    reviewed_by_gm: str
    submitted_by: str
    submitted_at: str
    updated_at: str
    confluence_page_id: str | None = None
    confluence_page_url: str | None = None


class SubmissionUpdateRequest(BaseModel):
    key_drivers_quantitative: str | None = None
    key_drivers_qualitative: str | None = None
    internal_factors: str | None = None
    external_factors: str | None = None
    oneoff_events: str | None = None
    planned_actions: str | None = None
    expected_impact: str | None = None
    sentiment_tags: str | None = None
    kpi_lockin: bool | None = None
    reviewed_by_gm: str | None = None


# --- Dashboard ---

class DashboardSummary(BaseModel):
    total_entries: int
    filled_entries: int
    locked_entries: int
    gm_reviewed_entries: int
    departments_reporting: int


class DepartmentDetail(BaseModel):
    department: DepartmentOut
    submissions: list[SubmissionOut]
    fill_rate: float
    lock_rate: float
    kpi_count: int


# --- Confluence ---

class ConfluencePublishResult(BaseModel):
    confluence_page_id: str
    confluence_page_url: str


class PublishSubmissionsSummaryRequest(BaseModel):
    department_name: str
    period: str | None = None


class PublishDashboardSummaryRequest(BaseModel):
    period: str | None = None


# --- Agent ---

class JustifyRequest(BaseModel):
    submission_id: str
    field: str  # e.g. "key_drivers_quantitative"


class NarrativeRequest(BaseModel):
    period: str  # e.g. "Jan 2026"


class NarrativeResponse(BaseModel):
    narrative: str


# --- Genie ---

class GenieSpaceUrl(BaseModel):
    url: str
    space_id: str


# --- AI/BI Dashboard ---

class AiBiDashboardUrl(BaseModel):
    url: str
    dashboard_id: str


class GenieAskRequest(BaseModel):
    content: str
    conversation_id: str | None = None


class GenieAttachment(BaseModel):
    text: str | None = None
    sql: str | None = None
    columns: list[str] = []
    data_array: list = []
    row_count: int = 0
    truncated: bool = False


class GenieAskResponse(BaseModel):
    # Optional because a FAILED/timed-out ask may have no conversation/message id
    # (e.g. start_conversation never reached a created message). The frontend
    # already handles status == "FAILED".
    conversation_id: str | None = None
    message_id: str | None = None
    status: str
    error: str | None = None  # Genie's own error text, present when status == "FAILED"
    attachments: list[GenieAttachment] = []


# --- Forecasting ---

class ForecastPoint(BaseModel):
    period: str       # e.g. "Apr 2026"
    actual: float | None = None
    low: float | None = None
    mid: float | None = None
    high: float | None = None
    is_forecast: bool = False


class KpiForecast(BaseModel):
    kpi_name: str
    kpi_unit: str
    points: list[ForecastPoint]
    insight: str      # 1-2 sentence Claude commentary


class ForecastResponse(BaseModel):
    forecasts: list[KpiForecast]
