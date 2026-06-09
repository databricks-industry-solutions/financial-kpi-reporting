from fastapi import APIRouter, HTTPException, Request

from .._metadata import api_prefix
from .dependencies import RuntimeDep, ConfigDep
from .models import (
    VersionOut,
    CurrentUser,
    DepartmentOut,
    SubmissionOut,
    SubmissionUpdateRequest,
    DashboardSummary,
    DepartmentDetail,
    ConfluencePublishResult,
    PublishSubmissionsSummaryRequest,
    PublishDashboardSummaryRequest,
    GenieSpaceUrl,
    GenieAskRequest,
    GenieAskResponse,
)
from .logger import logger

api = APIRouter(prefix=api_prefix)


@api.get("/version", response_model=VersionOut, operation_id="version")
async def version():
    return VersionOut.from_metadata()


# --- Current User ---

JOB_ROLE_MAP = {
    "General Manager": "gm",
    "Business Line Manager": "blm",
    "Business Controller": "bc",
}


@api.get("/me", response_model=CurrentUser, operation_id="getCurrentUser")
async def get_current_user(request: Request, runtime: RuntimeDep):
    email = request.headers.get("x-forwarded-email")
    display_name = request.headers.get("x-forwarded-preferred-username") or request.headers.get("x-forwarded-user")

    if not email:
        raise HTTPException(status_code=401, detail="Not authenticated")

    if not display_name:
        display_name = email.split("@")[0]

    # Look up in userbase
    entry = runtime.lakebase.get_userbase_entry(email)

    if entry:
        job = entry.get("job_name", "")
        role = JOB_ROLE_MAP.get(job, "viewer")
        # Resolve department ID from name
        depts = runtime.lakebase.get_departments()
        dept = next((d for d in depts if d["name"] == entry["department_name"]), None)
        return CurrentUser(
            email=email,
            name=entry.get("employee_name", display_name),
            department_name=entry["department_name"],
            department_id=dept["id"] if dept else None,
            operation_unit_code=entry.get("operation_unit_code"),
            job_name=job,
            role=role,
            is_executive=False,
        )

    # Not in userbase → fall back to demo personas
    logger.info(f"User {email} not in userbase, using demo fallback")
    depts = runtime.lakebase.get_departments()
    ne = next((d for d in depts if d["name"] == "Region North"), None)
    return CurrentUser(
        email=email,
        name=ne["lead_name"] if ne else display_name,
        department_name="Region North",
        department_id=ne["id"] if ne else None,
        operation_unit_code="REGN",
        job_name="General Manager",
        role="gm",
        is_executive=False,
    )


# --- Departments ---

@api.get("/departments", response_model=list[DepartmentOut], operation_id="getDepartments")
async def get_departments(runtime: RuntimeDep):
    rows = runtime.lakebase.get_departments()
    return [DepartmentOut(**row) for row in rows]


# --- Submissions ---

@api.get("/submissions", response_model=list[SubmissionOut], operation_id="getSubmissions")
async def get_submissions(
    runtime: RuntimeDep,
    department_id: str | None = None,
    period: str | None = None,
):
    rows = runtime.lakebase.get_submissions(
        department_id=department_id,
        period=period,
    )
    return [SubmissionOut(**row) for row in rows]


@api.get("/submissions/{sub_id}", response_model=SubmissionOut, operation_id="getSubmission")
async def get_submission(sub_id: str, runtime: RuntimeDep):
    row = runtime.lakebase.get_submission(sub_id)
    if not row:
        raise HTTPException(status_code=404, detail=f"Submission {sub_id} not found")
    return SubmissionOut(**row)


@api.put("/submissions/{sub_id}", response_model=SubmissionOut, operation_id="updateSubmission")
async def update_submission(sub_id: str, req: SubmissionUpdateRequest, runtime: RuntimeDep):
    data = {k: v for k, v in req.model_dump().items() if v is not None}
    row = runtime.lakebase.update_submission(sub_id, data)
    if not row:
        raise HTTPException(status_code=404, detail=f"Submission {sub_id} not found")
    logger.info(f"Updated submission: {sub_id}")
    return SubmissionOut(**row)


# --- Confluence ---

@api.post("/submissions/{sub_id}/publish-confluence", response_model=ConfluencePublishResult, operation_id="publishToConfluence")
async def publish_to_confluence(sub_id: str, runtime: RuntimeDep):
    submission = runtime.lakebase.get_submission(sub_id)
    if not submission:
        raise HTTPException(status_code=404, detail=f"Submission {sub_id} not found")

    if not runtime.confluence.enabled:
        raise HTTPException(status_code=400, detail="Confluence integration is not configured")

    existing_page_id = submission.get("confluence_page_id")
    result = await runtime.confluence.publish_submission(submission, existing_page_id)

    runtime.lakebase.update_submission_confluence(
        sub_id, result["confluence_page_id"], result["confluence_page_url"]
    )

    logger.info(f"Published submission {sub_id} to Confluence: {result['confluence_page_url']}")
    return ConfluencePublishResult(**result)


@api.post("/publish-submissions-summary", response_model=ConfluencePublishResult, operation_id="publishSubmissionsSummary")
async def publish_submissions_summary(req: PublishSubmissionsSummaryRequest, runtime: RuntimeDep):
    if not runtime.confluence.enabled:
        raise HTTPException(status_code=400, detail="Confluence integration is not configured")

    rows = runtime.lakebase.get_submissions(period=req.period)
    submissions = [r for r in rows if r["department_name"] == req.department_name]
    if not submissions:
        raise HTTPException(status_code=404, detail="No submissions match the current filters")

    body = runtime.confluence._build_submissions_summary_html(submissions, req.department_name, req.period)

    parts = ["Monthly KPI Report", req.department_name]
    if req.period:
        parts.append(req.period)
    title = " — ".join(parts)

    result = await runtime.confluence.publish_page(title, body)
    logger.info(f"Published submissions summary to Confluence: {result['confluence_page_url']}")
    return ConfluencePublishResult(**result)


@api.post("/publish-dashboard-summary", response_model=ConfluencePublishResult, operation_id="publishDashboardSummary")
async def publish_dashboard_summary(req: PublishDashboardSummaryRequest, runtime: RuntimeDep):
    if not runtime.confluence.enabled:
        raise HTTPException(status_code=400, detail="Confluence integration is not configured")

    summary = runtime.lakebase.get_dashboard_summary(req.period)
    departments = runtime.lakebase.get_departments()
    submissions = runtime.lakebase.get_submissions(period=req.period)

    dept_stats = []
    for dept in departments:
        dept_subs = [s for s in submissions if s["department_id"] == dept["id"]]
        total = len(dept_subs)
        filled = sum(1 for s in dept_subs if any(
            s.get(f) for f in ("key_drivers_quantitative", "key_drivers_qualitative", "internal_factors", "external_factors", "planned_actions", "expected_impact")
        ))
        locked = sum(1 for s in dept_subs if s.get("kpi_lockin"))
        dept_stats.append({
            "name": dept["name"],
            "lead_name": dept["lead_name"],
            "kpi_count": total,
            "filled": filled,
            "locked": locked,
            "fill_rate": round((filled / total) * 100, 1) if total > 0 else 0,
        })

    body = runtime.confluence._build_dashboard_summary_html(summary, dept_stats, req.period)

    title = "Monthly KPI Report — Executive Summary"
    if req.period:
        title += f" — {req.period}"

    result = await runtime.confluence.publish_page(title, body)
    logger.info(f"Published dashboard summary to Confluence: {result['confluence_page_url']}")
    return ConfluencePublishResult(**result)


# --- Dashboard ---

@api.get("/dashboard/summary", response_model=DashboardSummary, operation_id="getDashboardSummary")
async def get_dashboard_summary(runtime: RuntimeDep, period: str | None = None):
    summary = runtime.lakebase.get_dashboard_summary(period)
    return DashboardSummary(**summary)


@api.get("/dashboard/department/{dept_id}", response_model=DepartmentDetail, operation_id="getDepartmentDetail")
async def get_department_detail(dept_id: str, runtime: RuntimeDep, period: str | None = None):
    detail = runtime.lakebase.get_department_detail(dept_id, period)
    if not detail:
        raise HTTPException(status_code=404, detail=f"Department {dept_id} not found")
    return DepartmentDetail(**detail)


# --- Genie ---

@api.get("/genie/space-url", response_model=GenieSpaceUrl, operation_id="getGenieSpaceUrl")
async def get_genie_space_url(config: ConfigDep):
    if not config.genie_space_id:
        raise HTTPException(status_code=400, detail="Genie Space is not configured")
    if not config.databricks_host:
        raise HTTPException(status_code=400, detail="DATABRICKS_HOST is not configured")

    host = config.databricks_host.rstrip("/")
    if not host.startswith("http"):
        host = f"https://{host}"
    url = f"{host}/genie/rooms/{config.genie_space_id}"
    return GenieSpaceUrl(url=url, space_id=config.genie_space_id)


@api.post("/genie/ask", response_model=GenieAskResponse, operation_id="genieAsk")
async def genie_ask(req: GenieAskRequest, runtime: RuntimeDep, config: ConfigDep):
    if not config.genie_space_id:
        raise HTTPException(status_code=400, detail="Genie Space is not configured")

    try:
        result = await runtime.genie.ask(
            content=req.content,
            conversation_id=req.conversation_id,
        )
        return GenieAskResponse(**result)
    except Exception as e:
        logger.error(f"Genie ask failed: {e}")
        raise HTTPException(status_code=502, detail=f"Genie query failed: {e}")
