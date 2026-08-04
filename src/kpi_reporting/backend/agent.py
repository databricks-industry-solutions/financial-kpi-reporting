"""Agentic capabilities backed by AI Gateway + Claude Sonnet.

Two agents:
1. JustificationAgent  — drafts a KPI justification field from data signals.
2. NarrativeAgent      — drafts an executive narrative for all locked submissions.

Both stream SSE tokens back to the frontend.
"""
import asyncio
import json
import os
from collections.abc import AsyncIterator
from typing import Any

from databricks.sdk import WorkspaceClient
from openai import AsyncOpenAI

from .logger import logger

# ---------------------------------------------------------------------------
# AI Gateway client
# ---------------------------------------------------------------------------

_DEFAULT_AI_GATEWAY_URL = ""  # Derived at runtime from DATABRICKS_HOST / DATABRICKS_ORG_ID via config.get_ai_gateway_url()
_MODEL = "databricks-claude-sonnet-5"


def _get_ai_client(gateway_url: str | None = None) -> AsyncOpenAI:
    url = gateway_url or os.environ.get("KPI_REPORTING_AI_GATEWAY_URL", _DEFAULT_AI_GATEWAY_URL)
    # Databricks Apps injects DATABRICKS_TOKEN directly — use it first.
    # Fall back to SDK authentication for local dev.
    token = os.environ.get("DATABRICKS_TOKEN", "")
    if not token:
        try:
            ws = WorkspaceClient()
            auth = ws.config.authenticate()
            token = auth.get("Authorization", "").replace("Bearer ", "")
        except Exception:
            token = "token"
    return AsyncOpenAI(
        api_key=token or "token",
        base_url=url,
    )


# ---------------------------------------------------------------------------
# Field-specific system prompts
# ---------------------------------------------------------------------------

_FIELD_GUIDANCE: dict[str, str] = {
    "key_drivers_quantitative": (
        "Write 1-2 concise sentences with specific numbers: percentages, absolute values, "
        "period-on-period changes. Example: 'Revenue Growth +5.2% vs PY, driven by "
        "volume growth across core segments (+8% units). OPEX Ratio 0.4pp above target.'"
    ),
    "key_drivers_qualitative": (
        "Write 2-3 sentences describing the business narrative behind the numbers. "
        "Focus on market dynamics, product mix, customer behaviour, or competitive context."
    ),
    "internal_factors": (
        "List 1-3 internal factors within the organization's control that influenced this KPI. "
        "Examples: staffing changes, process improvements, ERP issues, capacity changes."
    ),
    "external_factors": (
        "List 1-3 external factors outside the organization's control. "
        "Examples: market demand, currency, raw material prices, regulation, competitor moves."
    ),
    "oneoff_events": (
        "Describe any non-recurring items. If none, leave empty. "
        "Examples: large one-time orders, warranty settlements, insurance recoveries."
    ),
    "planned_actions": (
        "Describe 2-3 concrete actions planned to address the KPI result. "
        "Be specific: what will be done, by whom, by when."
    ),
    "expected_impact": (
        "Quantify or qualify the expected outcome of the planned actions in the next 1-3 months."
    ),
}

# ---------------------------------------------------------------------------
# Justification Agent
# ---------------------------------------------------------------------------

_JUSTIFY_SYSTEM = """You are a financial business controller writing
KPI justifications for the monthly management report. Be concise, data-driven and
professional. Use the specific KPI data and context provided. Do NOT invent numbers
not given to you. Output only the justification text — no headers, no preamble."""


def _build_justify_prompt(
    field: str,
    submission: dict[str, Any],
    peer_submissions: list[dict[str, Any]],
    prior_submissions: list[dict[str, Any]],
    genie_context: str,
) -> str:
    kpi_name = submission.get("kpi_name", "")
    kpi_value = submission.get("kpi_value")
    kpi_unit = submission.get("kpi_unit", "")
    dept = submission.get("department_name", "")
    period = submission.get("period", "")
    category = submission.get("kpi_category", "")

    # Format peer data
    peer_lines = []
    for p in peer_submissions[:4]:
        v = p.get("kpi_value")
        if v is not None:
            peer_lines.append(f"  - {p['department_name']}: {v} {kpi_unit}")

    # Format prior periods
    prior_lines = []
    for p in sorted(prior_submissions, key=lambda x: x.get("period", ""), reverse=True)[:3]:
        v = p.get("kpi_value")
        if v is not None:
            prior_lines.append(f"  - {p['period']}: {v} {kpi_unit}")
        existing = p.get(field, "")
        if existing:
            prior_lines.append(f"    Justification: {existing[:120]}...")

    parts = [
        f"KPI: {kpi_name} ({category})",
        f"Region/Department: {dept}",
        f"Period: {period}",
        f"Current value: {kpi_value} {kpi_unit}" if kpi_value is not None else "Current value: not yet recorded",
    ]

    if prior_lines:
        parts.append(f"\nPrior periods for comparison:\n" + "\n".join(prior_lines))

    if peer_lines:
        parts.append(f"\nPeer regions this period:\n" + "\n".join(peer_lines))

    if genie_context:
        parts.append(f"\nAdditional data from Genie:\n{genie_context}")

    field_instruction = _FIELD_GUIDANCE.get(field, "Write a professional justification.")
    parts.append(f"\nField to fill in: {field.replace('_', ' ').title()}")
    parts.append(f"Instructions: {field_instruction}")

    return "\n".join(parts)


async def stream_justification(
    field: str,
    submission: dict[str, Any],
    peer_submissions: list[dict[str, Any]],
    prior_submissions: list[dict[str, Any]],
    genie_context: str = "",
    gateway_url: str | None = None,
) -> AsyncIterator[str]:
    """Stream SSE-formatted tokens for a justification draft."""
    client = _get_ai_client(gateway_url)
    prompt = _build_justify_prompt(field, submission, peer_submissions, prior_submissions, genie_context)

    logger.info(f"JustificationAgent: field={field}, dept={submission.get('department_name')}, kpi={submission.get('kpi_name')}")

    try:
        stream = await client.chat.completions.create(
            model=_MODEL,
            messages=[
                {"role": "system", "content": _JUSTIFY_SYSTEM},
                {"role": "user", "content": prompt},
            ],
            max_tokens=300,
            stream=True,
        )
        async for chunk in stream:
            delta = chunk.choices[0].delta.content if chunk.choices else None
            if delta:
                yield f"data: {json.dumps({'token': delta})}\n\n"
        yield "data: {\"done\": true}\n\n"
    except Exception as e:
        logger.error(f"JustificationAgent error: {e}")
        yield f"data: {json.dumps({'error': str(e)})}\n\n"


# ---------------------------------------------------------------------------
# Narrative Agent (Feature 3: Executive)
# ---------------------------------------------------------------------------

_NARRATIVE_SYSTEM = """You are drafting an executive management narrative for the
monthly KPI report. The audience is senior leadership. Be structured, insightful and concise.
Use actual numbers from the data. Highlight what went well, what needs attention, risks, and outlook.

Output format (use markdown with these exact headers):
## Highlights
## Areas of Attention
## Risks & External Factors
## Outlook & Planned Actions"""


def _build_narrative_prompt(
    period: str,
    departments: list[dict[str, Any]],
    submissions: list[dict[str, Any]],
) -> str:
    # Group by dept
    dept_map = {d["id"]: d["name"] for d in departments}

    # Summarise per KPI per dept
    summary_lines = []
    kpi_names = sorted(set(s["kpi_name"] for s in submissions))

    for kpi in kpi_names:
        kpi_subs = [s for s in submissions if s["kpi_name"] == kpi]
        summary_lines.append(f"\n### {kpi}")
        for s in kpi_subs:
            dept_name = s.get("department_name", dept_map.get(s.get("department_id", ""), "Unknown"))
            v = s.get("kpi_value")
            unit = s.get("kpi_unit", "")
            value_str = f"{v} {unit}" if v is not None else "n/a"
            sentiment = s.get("sentiment_tags", "")
            quant = s.get("key_drivers_quantitative", "")
            qual = s.get("key_drivers_qualitative", "")
            planned = s.get("planned_actions", "")
            summary_lines.append(
                f"- **{dept_name}**: {value_str} | Sentiment: {sentiment or 'n/a'}"
            )
            if quant:
                summary_lines.append(f"  Quant: {quant[:120]}")
            if qual:
                summary_lines.append(f"  Qual: {qual[:120]}")
            if planned:
                summary_lines.append(f"  Actions: {planned[:100]}")

    locked = sum(1 for s in submissions if s.get("kpi_lockin"))
    total = len(submissions)
    fill_rate = round(100 * sum(1 for s in submissions if any(s.get(f) for f in (
        "key_drivers_quantitative", "key_drivers_qualitative",
        "internal_factors", "external_factors"
    ))) / total, 1) if total else 0

    header = (
        f"Period: {period}\n"
        f"Reporting status: {locked}/{total} KPIs locked in | Fill rate: {fill_rate}%\n"
        f"Departments reporting: {len(set(s.get('department_name') for s in submissions))}\n"
    )

    return header + "\n".join(summary_lines)


async def stream_narrative(
    period: str,
    departments: list[dict[str, Any]],
    submissions: list[dict[str, Any]],
    gateway_url: str | None = None,
) -> AsyncIterator[str]:
    """Stream SSE-formatted tokens for the executive narrative."""
    client = _get_ai_client(gateway_url)
    prompt = _build_narrative_prompt(period, departments, submissions)

    logger.info(f"NarrativeAgent: period={period}, submissions={len(submissions)}")

    try:
        stream = await client.chat.completions.create(
            model=_MODEL,
            messages=[
                {"role": "system", "content": _NARRATIVE_SYSTEM},
                {"role": "user", "content": prompt},
            ],
            max_tokens=900,
            stream=True,
        )
        async for chunk in stream:
            delta = chunk.choices[0].delta.content if chunk.choices else None
            if delta:
                yield f"data: {json.dumps({'token': delta})}\n\n"
        yield "data: {\"done\": true}\n\n"
    except Exception as e:
        logger.error(f"NarrativeAgent error: {e}")
        yield f"data: {json.dumps({'error': str(e)})}\n\n"
