from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import StreamingResponse
from pydantic import BaseModel

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
    JustifyRequest,
    NarrativeRequest,
    NarrativeResponse,
    AiBiDashboardUrl,
    TaskItem,
    TaskAction,
    TasksResponse,
    RiskReport,
    RiskItem,
    RegionRiskSummary,
    ForecastPoint,
    KpiForecast,
    ForecastResponse,
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
        operation_unit_code="REGNOR",
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


@api.get("/aibi/dashboard-url", response_model=AiBiDashboardUrl, operation_id="getAiBiDashboardUrl")
async def get_aibi_dashboard_url(config: ConfigDep):
    """Return the embedded AI/BI dashboard URL for the analytics tab."""
    if not config.aibi_dashboard_id:
        raise HTTPException(status_code=404, detail="AI/BI dashboard is not configured")
    host = config.databricks_host.rstrip("/")
    if host and not host.startswith("http"):
        host = f"https://{host}"
    # Use /embed/ path — sets frame-ancestors: * so the iframe is allowed from any origin.
    # The plain /dashboardsv3/.../published path redirects to /login.html which has
    # X-Frame-Options: DENY, causing "refused to connect" in the iframe.
    url = f"{host}/embed/dashboardsv3/{config.aibi_dashboard_id}/published"
    return AiBiDashboardUrl(url=url, dashboard_id=config.aibi_dashboard_id)


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


# --- Agent ---

_VALID_JUSTIFY_FIELDS = {
    "key_drivers_quantitative", "key_drivers_qualitative",
    "internal_factors", "external_factors",
    "oneoff_events", "planned_actions", "expected_impact",
}


@api.post("/agent/justify", operation_id="agentJustify")
async def agent_justify(req: JustifyRequest, runtime: RuntimeDep, config: ConfigDep):
    """Stream a drafted justification for a single KPI field via SSE."""
    if req.field not in _VALID_JUSTIFY_FIELDS:
        raise HTTPException(status_code=400, detail=f"Unknown field: {req.field}")

    submission = runtime.lakebase.get_submission(req.submission_id)
    if not submission:
        raise HTTPException(status_code=404, detail=f"Submission {req.submission_id} not found")

    # Peer submissions: same KPI + period, other regions
    all_same_kpi = runtime.lakebase.get_submissions(period=submission["period"])
    peer_submissions = [
        s for s in all_same_kpi
        if s["kpi_name"] == submission["kpi_name"] and s["id"] != submission["id"]
    ]

    # Prior periods: same region + KPI, chronologically before this period.
    # Filter on period_start (a DATE) so future months are never treated as
    # "prior" — the period label ("Jul 2025") is not chronologically sortable.
    all_dept = runtime.lakebase.get_submissions(department_id=submission["department_id"])
    prior_submissions = [
        s for s in all_dept
        if s["kpi_name"] == submission["kpi_name"]
        and s["period_start"] < submission["period_start"]
    ]

    gateway_url = config.get_ai_gateway_url()
    if not gateway_url:
        raise HTTPException(status_code=503, detail="AI Gateway is not configured. Run notebook 03 to set up the AI Gateway URL.")

    from .agent import stream_justification
    return StreamingResponse(
        stream_justification(req.field, submission, peer_submissions, prior_submissions, gateway_url=gateway_url),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )


@api.post("/agent/narrative", response_model=NarrativeResponse, operation_id="agentNarrative")
async def agent_narrative(req: NarrativeRequest, runtime: RuntimeDep, config: ConfigDep):
    """Generate an executive narrative for the given period (non-streaming)."""
    from .agent import _get_ai_client, _build_narrative_prompt, _NARRATIVE_SYSTEM, _MODEL

    submissions = runtime.lakebase.get_submissions(period=req.period)
    if not submissions:
        raise HTTPException(status_code=404, detail=f"No submissions found for period {req.period}")

    gateway_url = config.get_ai_gateway_url()
    if not gateway_url:
        raise HTTPException(status_code=503, detail="AI Gateway is not configured. Run notebook 03 to set up the AI Gateway URL.")

    departments = runtime.lakebase.get_departments()
    prompt = _build_narrative_prompt(req.period, departments, submissions)

    client = _get_ai_client(gateway_url)
    response = await client.chat.completions.create(
        model=_MODEL,
        messages=[
            {"role": "system", "content": _NARRATIVE_SYSTEM},
            {"role": "user", "content": prompt},
        ],
        max_tokens=4096,
    )
    raw = response.choices[0].message.content
    # Claude Sonnet 5 returns content as a list of blocks when extended thinking fires:
    # [{"type": "reasoning", ...}, {"type": "text", "text": "..."}]
    # Extract all text blocks and join them.
    if isinstance(raw, list):
        parts = []
        for block in raw:
            if isinstance(block, dict) and block.get("type") == "text":
                parts.append(block.get("text", ""))
            elif hasattr(block, "type") and getattr(block, "type", None) == "text":
                parts.append(getattr(block, "text", ""))
        narrative = "".join(parts)
    else:
        narrative = raw or ""
    if not narrative:
        logger.warning(f"NarrativeEmpty: raw type={type(raw).__name__} blocks={len(raw) if isinstance(raw, list) else 'n/a'}")
    return NarrativeResponse(narrative=narrative)



# ---------------------------------------------------------------------------
# Forecast endpoint
# ---------------------------------------------------------------------------

@api.get("/forecast/kpi", response_model=ForecastResponse, operation_id="getKpiForecast")
async def get_kpi_forecast(runtime: RuntimeDep):
    """
    Return 3-month ahead forecasts for the main KPIs using linear regression + seasonality.
    Single DB query, no LLM call — sub-second response.
    """
    N_FORECAST = 3

    # Data-driven: forecast whatever KPIs and periods are actually present, so this
    # works for any KPI set defined in notebook 01. Ordering is by period_start (a
    # real date), never by the "Mon YYYY" display string.
    rows = runtime.lakebase.execute(
        """
        SELECT kpi_name, kpi_unit,
               MIN(kpi_number) AS kpi_number,
               TO_CHAR(period_start, 'Mon YYYY') AS period_label,
               MIN(period_start) AS period_start,
               SUM(kpi_value) AS total_value
        FROM kpi_submissions
        WHERE kpi_value IS NOT NULL
        GROUP BY kpi_name, kpi_unit, period_start
        ORDER BY MIN(kpi_number), kpi_name, period_start
        """,
        {},
    )

    # Chronological period order, derived from the data.
    _period_starts: dict[str, str] = {}
    for r in rows:
        _period_starts.setdefault(r["period_label"], str(r["period_start"]))
    PERIOD_ORDER = sorted(_period_starts, key=lambda p: _period_starts[p])

    # KPI order follows kpi_number, matching how the KPIs are numbered in notebook 01.
    KPI_CONFIGS: list[tuple[str, str]] = []
    _seen: set[tuple[str, str]] = set()
    for r in sorted(rows, key=lambda r: (r["kpi_number"], r["kpi_name"])):
        key = (r["kpi_name"], r["kpi_unit"])
        if key not in _seen:
            _seen.add(key)
            KPI_CONFIGS.append(key)

    def _next_periods(last_label: str, n: int) -> list[str]:
        """Continue the monthly sequence n months past `last_label` ("Mon YYYY")."""
        from datetime import datetime

        try:
            d = datetime.strptime(last_label, "%b %Y")
        except ValueError:
            return []
        out = []
        year, month = d.year, d.month
        for _ in range(n):
            month += 1
            if month > 12:
                month = 1
                year += 1
            out.append(datetime(year, month, 1).strftime("%b %Y"))
        return out

    FORECAST_PERIODS = _next_periods(PERIOD_ORDER[-1], N_FORECAST) if PERIOD_ORDER else []

    KPI_SET = set(KPI_CONFIGS)

    # Group into {(name, unit): {period: value}}
    raw_data: dict[tuple[str, str], dict[str, float]] = {k: {} for k in KPI_SET}
    for r in rows:
        key = (r["kpi_name"], r["kpi_unit"])
        if key in raw_data:
            raw_data[key][r["period_label"]] = float(r["total_value"])

    # --- 2. Linear regression forecast per KPI (stdlib only, no numpy) ---
    def _linreg_forecast(values: list[float], n_forecast: int, confidence: float = 0.08):
        """Simple OLS linear trend + ±confidence band."""
        n = len(values)
        if n < 2:
            last = values[-1] if values else 0.0
            return [(last, last, last)] * n_forecast
        xs = list(range(n))
        mx = sum(xs) / n
        my = sum(values) / n
        ss_xy = sum((x - mx) * (y - my) for x, y in zip(xs, values))
        ss_xx = sum((x - mx) ** 2 for x in xs)
        slope = ss_xy / ss_xx if ss_xx else 0.0
        intercept = my - slope * mx
        result = []
        for i in range(n, n + n_forecast):
            mid = intercept + slope * i
            band = abs(mid) * confidence
            result.append((round(mid - band, 2), round(mid, 2), round(mid + band, 2)))
        return result

    def _trend_insight(name: str, unit: str, values: list[float]) -> str:
        if len(values) < 2:
            return f"{name} data is limited; forecast confidence is low."
        recent = values[-3:]
        avg_recent = sum(recent) / len(recent)
        avg_all = sum(values) / len(values)
        delta_pct = ((avg_recent - avg_all) / avg_all * 100) if avg_all else 0
        direction = "trending upward" if delta_pct > 2 else "trending downward" if delta_pct < -2 else "broadly stable"
        return (
            f"{name} ({unit}) is {direction} with a recent average of "
            f"{avg_recent:.1f} {unit} vs. {avg_all:.1f} {unit} overall."
        )

    # --- 3. Build response ---
    forecasts: list[KpiForecast] = []
    for kpi_name, kpi_unit in KPI_CONFIGS:
        actuals = raw_data.get((kpi_name, kpi_unit), {})
        ordered_values = [actuals[p] for p in PERIOD_ORDER if p in actuals]
        if not ordered_values:
            continue

        fc_points = _linreg_forecast(ordered_values, len(FORECAST_PERIODS))

        points: list[ForecastPoint] = []
        for p in PERIOD_ORDER:
            if p in actuals:
                points.append(ForecastPoint(period=p, actual=actuals[p], is_forecast=False))
        for p, (low, mid, high) in zip(FORECAST_PERIODS, fc_points):
            points.append(ForecastPoint(period=p, low=low, mid=mid, high=high, is_forecast=True))

        forecasts.append(KpiForecast(
            kpi_name=kpi_name,
            kpi_unit=kpi_unit,
            points=points,
            insight=_trend_insight(kpi_name, kpi_unit, ordered_values),
        ))

    return ForecastResponse(forecasts=forecasts)


# ---------------------------------------------------------------------------
# Tasks endpoint — drives the home page for GM and CFO personas
# ---------------------------------------------------------------------------

def _period_sort_key(period_label: str):
    """Sort key for a "Mon YYYY" period label.

    Parses the label into a real date so periods order chronologically for any
    date range. Unparseable labels sort last.
    """
    from datetime import datetime

    try:
        return (0, datetime.strptime(period_label, "%b %Y"))
    except ValueError:
        return (1, datetime.min)


@api.get("/tasks", response_model=TasksResponse, operation_id="getTasks")
async def get_tasks(persona: str, runtime: RuntimeDep, department_id: str | None = None):
    """
    Return persona-specific tasks.
    persona = "gm"  -> regional lead: unfilled KPI justifications for their region
    persona = "cfo" -> executive: periods with unlocked / unjustified submissions to review
    """
    import uuid

    tasks: list[TaskItem] = []

    if persona == "gm":
        # For each period (most recent first), find submissions for the lead's region.
        # If no department_id passed, fall back to first region (demo persona dept).
        dept_id = department_id
        if not dept_id:
            depts = runtime.lakebase.get_departments()
            ne = next((d for d in depts if d["name"] == "Region North"), None)
            dept_id = ne["id"] if ne else None

        all_subs = runtime.lakebase.get_submissions(department_id=dept_id) if dept_id else []

        # Group by period, find the most recent open one
        by_period: dict[str, list] = {}
        for s in all_subs:
            p = s.get("period_label") or s.get("period", "")
            by_period.setdefault(p, []).append(s)

        # Sort periods newest first using PERIOD_ORDER
        sorted_periods = sorted(
            by_period.keys(),
            key=_period_sort_key,
            reverse=True,
        )

        active_period = sorted_periods[0] if sorted_periods else ""

        for period in sorted_periods[:3]:  # show tasks for up to last 3 periods
            subs = by_period[period]
            total = len(subs)
            needs_justification = [
                s for s in subs
                if not s.get("kpi_lockin") or not any(
                    s.get(f) for f in ("key_drivers_quantitative", "key_drivers_qualitative",
                                       "internal_factors", "external_factors")
                )
            ]
            count = len(needs_justification)
            if count == 0:
                status = "done"
            elif count < total:
                status = "in_progress"
            else:
                status = "pending"

            tasks.append(TaskItem(
                id=str(uuid.uuid4()),
                title=f"Submit KPI justifications — {period}",
                description=(
                    f"All {total} KPIs justified and locked." if status == "done"
                    else f"{count} of {total} KPIs still need justification or sign-off."
                ),
                period=period,
                status=status,
                count=count,
                total=total,
                route="/kpi-submission",
            ))

        return TasksResponse(tasks=tasks, period=active_period)

    elif persona == "cfo":
        all_subs = runtime.lakebase.get_submissions()

        by_period: dict[str, list] = {}
        for s in all_subs:
            p = s.get("period_label") or s.get("period", "")
            by_period.setdefault(p, []).append(s)

        sorted_periods = sorted(
            by_period.keys(),
            key=_period_sort_key,
            reverse=True,
        )

        # Skip periods with zero submissions — nothing to review yet
        periods_with_data = [
            p for p in sorted_periods
            if any(s.get("kpi_lockin") or any(
                s.get(f) for f in ("key_drivers_quantitative", "key_drivers_qualitative",
                                   "internal_factors", "external_factors")
            ) for s in by_period[p])
        ]

        active_period = periods_with_data[0] if periods_with_data else (sorted_periods[0] if sorted_periods else "")

        for period in periods_with_data[:3]:
            subs = by_period[period]
            total = len(subs)
            locked = sum(1 for s in subs if s.get("kpi_lockin"))
            justified = sum(1 for s in subs if any(
                s.get(f) for f in ("key_drivers_quantitative", "key_drivers_qualitative",
                                   "internal_factors", "external_factors")
            ))

            # Flag bad/cautious sentiment
            negative = [
                s for s in subs
                if s.get("sentiment_tags", "").lower() in ("negative", "cautious", "at risk")
            ]
            unlocked = total - locked

            if locked == total and justified == total and not negative:
                status = "done"
                desc = f"All {total} KPIs locked and justified — no issues flagged."
            else:
                status = "in_progress" if locked > 0 or justified > 0 else "pending"
                parts = []
                if unlocked > 0:
                    parts.append(f"{unlocked} KPI{'s' if unlocked > 1 else ''} not yet locked")
                if negative:
                    dept_names = list({s.get("department_name", "Unknown") for s in negative})
                    kpi_names = list({s.get("kpi_name", "") for s in negative})
                    parts.append(
                        f"{len(negative)} flagged with cautious/negative sentiment"
                        f" ({', '.join(kpi_names[:3])})"
                        f" — {', '.join(dept_names[:3])}"
                    )
                desc = " · ".join(parts) if parts else f"{justified}/{total} justified · {locked}/{total} locked."

            # Build context-driven actions
            period_actions: list[TaskAction] = []

            if status == "done":
                # Everything locked and clean — only offer narrative
                period_actions.append(TaskAction(
                    label="Executive Narrative",
                    route="/executive-dashboard",
                    variant="outline",
                ))
            else:
                # Always offer overview of the period
                period_actions.append(TaskAction(
                    label="Review KPIs",
                    route="/executive-dashboard",
                    variant="default",
                ))
                # If there are cautious/negative entries → push to risk analysis
                if len(negative) >= 3:
                    period_actions.append(TaskAction(
                        label=f"Risk Analysis ({len(negative)} flags)",
                        route="/risk-report",
                        variant="destructive",
                    ))
                elif len(negative) > 0:
                    period_actions.append(TaskAction(
                        label=f"View {len(negative)} Risk Flag{'s' if len(negative) > 1 else ''}",
                        route="/risk-report",
                        variant="outline",
                    ))

            tasks.append(TaskItem(
                id=str(uuid.uuid4()),
                title=f"{period}",
                description=desc,
                period=period,
                status=status,
                count=None,
                total=total,
                unlocked_count=unlocked,
                negative_count=len(negative),
                route="/executive-dashboard",
                actions=period_actions,
            ))

        return TasksResponse(tasks=tasks, period=active_period)

    raise HTTPException(status_code=400, detail=f"Unknown persona: {persona}")


# ---------------------------------------------------------------------------
# Risk Report endpoint
# ---------------------------------------------------------------------------

class RiskReportRequest(BaseModel):
    period: str


_RISK_SYSTEM = """You are a senior financial risk analyst reviewing KPI submissions from regional business units.
Analyse the data and return a structured JSON risk report. Be specific — quote actual values and department names.
Base your analysis ONLY on the provided submission data. Return ONLY valid JSON, no markdown fences."""

_RISK_PROMPT_TEMPLATE = """
Period: {period}
Total submissions: {total} across {cc_count} business units

---
SUBMISSION DATA (one entry per KPI per region):
{submissions_text}
---

Produce a risk report in this EXACT JSON structure:
{{
  "executive_summary": "2-3 sentence overall picture for the CFO.",
  "top_risks": [
    {{
      "rank": 1,
      "title": "Short risk title",
      "severity": "high",
      "affected_regions": ["Region North"],
      "affected_kpis": ["Revenue Growth", "OPEX Ratio"],
      "evidence": "Specific quote or data point from the submissions.",
      "recommended_action": "Concrete action for the CFO to consider."
    }}
  ],
  "region_summaries": [
    {{
      "region_name": "Region North",
      "overall_sentiment": "positive",
      "risk_level": "low",
      "headline": "One sentence summary.",
      "kpi_sentiments": {{"Revenue Growth": "positive", "Operating Margin": "neutral"}}
    }}
  ],
  "cross_cutting_patterns": "1-2 sentences about patterns across multiple regions.",
  "outlook": "1-2 sentences forward-looking outlook."
}}

Rules:
- top_risks: 3-5 items, ranked by severity. Only include real risks from the data.
- region_summaries: one entry per region in the data.
- severity: "high" | "medium" | "low"
- overall_sentiment / kpi_sentiments values: "positive" | "neutral" | "cautious" | "negative"
- risk_level: "high" | "medium" | "low" | "none"
"""


def _build_risk_prompt(period: str, submissions: list[dict]) -> str:
    lines = []
    for s in submissions:
        dept = s.get("department_name", "Unknown")
        kpi = s.get("kpi_name", "")
        val = s.get("kpi_value")
        unit = s.get("kpi_unit", "")
        sentiment = s.get("sentiment_tags", "n/a")
        quant = s.get("key_drivers_quantitative", "")
        qual = s.get("key_drivers_qualitative", "")
        internal = s.get("internal_factors", "")
        external = s.get("external_factors", "")
        actions = s.get("planned_actions", "")

        # Keep per-entry compact to stay within token budget
        entry = f"[{dept} | {kpi}: {val} {unit} | Sentiment: {sentiment}]"
        # Combine all text fields, pick the most informative 200 chars total
        text_parts = [t for t in [quant, qual, internal, external] if t]
        combined = " | ".join(text_parts)[:200]
        if combined:
            entry += f"\n  {combined}"
        if actions:
            entry += f"\n  Actions: {actions[:80]}"
        lines.append(entry)

    subs_text = "\n\n".join(lines)
    cc_count = len(set(s.get("department_name") for s in submissions))

    return _RISK_PROMPT_TEMPLATE.format(
        period=period,
        total=len(submissions),
        cc_count=cc_count,
        submissions_text=subs_text,
    )


@api.post("/agent/risk-report", response_model=RiskReport, operation_id="generateRiskReport")
async def generate_risk_report(req: RiskReportRequest, runtime: RuntimeDep, config: ConfigDep):
    """Generate an AI risk report for the given period."""
    import json as _json
    from datetime import datetime, timezone
    from .agent import _get_ai_client, _MODEL

    submissions = runtime.lakebase.get_submissions(period=req.period)
    # Only analyse filled submissions — no point analysing blanks
    filled = [s for s in submissions if any(
        s.get(f) for f in ("key_drivers_quantitative", "key_drivers_qualitative",
                           "internal_factors", "external_factors")
    )]
    if not filled:
        # Find the latest period that has filled submissions to give a helpful hint.
        all_submissions = runtime.lakebase.get_submissions()
        all_filled = [s for s in all_submissions if any(
            s.get(f) for f in ("key_drivers_quantitative", "key_drivers_qualitative",
                               "internal_factors", "external_factors")
        )]
        if all_filled:
            # Sort by period_start descending to find the most recent filled period.
            def _period_key(s):
                try:
                    return str(s.get("period_start") or "")
                except Exception:
                    return ""
            latest = max(all_filled, key=_period_key)
            latest_period = latest.get("period", "unknown")
            raise HTTPException(status_code=404, detail=f"No filled submissions found for {req.period}. Latest submission is for {latest_period}.")
        else:
            raise HTTPException(status_code=404, detail=f"No filled submissions found for {req.period}. Please run the setup notebooks and ensure KPI justifications have been submitted.")

    gateway_url = config.get_ai_gateway_url()
    if not gateway_url:
        raise HTTPException(status_code=503, detail="AI Gateway is not configured. Run notebook 03 to set up the AI Gateway URL, or set the KPI_REPORTING_AI_GATEWAY_URL environment variable.")

    prompt = _build_risk_prompt(req.period, filled)
    client = _get_ai_client(gateway_url)

    response = await client.chat.completions.create(
        model=_MODEL,
        messages=[
            {"role": "system", "content": _RISK_SYSTEM},
            {"role": "user", "content": prompt},
        ],
        max_tokens=8192,
    )

    raw = response.choices[0].message.content
    if isinstance(raw, list):
        text = "".join(
            b.get("text", "") if isinstance(b, dict) else getattr(b, "text", "")
            for b in raw
            if (isinstance(b, dict) and b.get("type") == "text")
            or (hasattr(b, "type") and getattr(b, "type") == "text")
        )
    else:
        text = raw or ""

    # Strip markdown fences if present
    text = text.strip()
    if text.startswith("```"):
        text = "\n".join(text.split("\n")[1:])
    if text.endswith("```"):
        text = "\n".join(text.split("\n")[:-1])
    text = text.strip()

    try:
        data = _json.loads(text)
    except Exception as e:
        # Try to extract a valid JSON object even if truncated
        logger.warning(f"RiskReport initial parse failed: {e} — attempting recovery")
        try:
            # Find last complete top-level brace pair
            last_brace = text.rfind("}")
            if last_brace > 0:
                data = _json.loads(text[:last_brace + 1])
            else:
                raise ValueError("No closing brace found")
        except Exception as e2:
            logger.error(f"RiskReport JSON recovery failed: {e2}\n{text[:300]}")
            raise HTTPException(status_code=500, detail="Risk model returned invalid JSON")

    def _norm_risk(r: dict) -> dict:
        """Normalise field name variants Claude might use."""
        out = dict(r)
        if "affected_units" in out and "affected_regions" not in out:
            out["affected_regions"] = out.pop("affected_units")
        elif "affected_departments" in out and "affected_regions" not in out:
            out["affected_regions"] = out.pop("affected_departments")
        return out

    def _norm_cc(s: dict) -> dict:
        out = dict(s)
        if "unit_name" in out and "region_name" not in out:
            out["region_name"] = out.pop("unit_name")
        elif "department_name" in out and "region_name" not in out:
            out["region_name"] = out.pop("department_name")
        return out

    return RiskReport(
        period=req.period,
        generated_at=datetime.now(timezone.utc).isoformat(),
        executive_summary=data.get("executive_summary", ""),
        top_risks=[RiskItem(**_norm_risk(r)) for r in data.get("top_risks", [])],
        region_summaries=[RegionRiskSummary(**_norm_cc(s)) for s in data.get("region_summaries", [])],
        cross_cutting_patterns=data.get("cross_cutting_patterns", ""),
        outlook=data.get("outlook", ""),
    )


@api.post("/agent/risk-report/publish-confluence", response_model=ConfluencePublishResult, operation_id="publishRiskReport")
async def publish_risk_report(report: RiskReport, runtime: RuntimeDep):
    """Publish an already-generated risk report to Confluence."""
    if not runtime.confluence.enabled:
        raise HTTPException(status_code=400, detail="Confluence integration is not configured")

    title = f"Risk & Sentiment Report — {report.period}"
    body = runtime.confluence._build_risk_report_html(report.model_dump())
    result = await runtime.confluence.publish_page(title, body)
    logger.info(f"Published risk report to Confluence: {result['confluence_page_url']}")
    return result
