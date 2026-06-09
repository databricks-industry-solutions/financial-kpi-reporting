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


# --- Genie ---

class GenieSpaceUrl(BaseModel):
    url: str
    space_id: str


class GenieAskRequest(BaseModel):
    content: str
    conversation_id: str | None = None


class GenieAttachment(BaseModel):
    text: str | None = None
    sql: str | None = None
    columns: list[str] = []
    data_array: list[list[str]] = []
    row_count: int = 0
    truncated: bool = False


class GenieAskResponse(BaseModel):
    conversation_id: str
    message_id: str
    status: str
    attachments: list[GenieAttachment] = []
