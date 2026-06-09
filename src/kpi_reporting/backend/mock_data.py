"""Mock data layer for local development without Lakebase."""

from datetime import datetime
import random as _random

# ---- Regions ----

DEPARTMENTS = [
    {"id": "d1000001-0000-0000-0000-000000000001", "name": "Region North", "lead_name": "Alex Morgan", "created_at": "2025-01-01T00:00:00"},
    {"id": "d1000001-0000-0000-0000-000000000002", "name": "Region South", "lead_name": "Priya Patel", "created_at": "2025-01-01T00:00:00"},
    {"id": "d1000001-0000-0000-0000-000000000003", "name": "Region East", "lead_name": "Jin Park", "created_at": "2025-01-01T00:00:00"},
    {"id": "d1000001-0000-0000-0000-000000000004", "name": "Region West", "lead_name": "Marcus Hill", "created_at": "2025-01-01T00:00:00"},
    {"id": "d1000001-0000-0000-0000-000000000005", "name": "Region Central", "lead_name": "Sofia Lopez", "created_at": "2025-01-01T00:00:00"},
    {"id": "d1000001-0000-0000-0000-000000000006", "name": "Region International", "lead_name": "Noah Schmidt", "created_at": "2025-01-01T00:00:00"},
]

# ---- 5 Fixed KPIs ----

KPI_DEFINITIONS = [
    {"name": "Revenue Growth", "number": 1, "category": "Revenue", "base_value": 8.5, "unit": "%", "variance": 0.18},
    {"name": "Operating Margin", "number": 2, "category": "Profitability", "base_value": 14.0, "unit": "%", "variance": 0.10},
    {"name": "DSO", "number": 3, "category": "Working Capital", "base_value": 52, "unit": "days", "variance": 0.12},
    {"name": "OPEX Ratio", "number": 4, "category": "Cost Control", "base_value": 22.0, "unit": "%", "variance": 0.08},
    {"name": "Free Cash Flow", "number": 5, "category": "Cash Flow", "base_value": 4200000, "unit": "USD", "variance": 0.20},
]

# ---- Submission generation ----

_RNG = _random.Random(42)

_HISTORICAL_MONTHS = [
    "Jan 2025", "Feb 2025", "Mar 2025", "Apr 2025", "May 2025", "Jun 2025",
    "Jul 2025", "Aug 2025", "Sep 2025", "Oct 2025", "Nov 2025", "Dec 2025",
    "Jan 2026",
]

_QUANT_DRIVERS = [
    "Revenue up 5.2% vs PY driven by volume growth across core segments",
    "Margin compression of 1.8pp from input cost inflation",
    "Order intake +12% vs budget; backlog conversion ahead of plan",
    "Recurring revenue flat YoY; new bookings +8% sequentially",
    "Headcount +3 FTE vs plan, increasing OPEX baseline",
    "Forecast accuracy improved to 92% from 87% last month",
    "DSO down 4 days; collections initiative gaining traction",
    "Mix shift towards higher-margin product lines",
    "FX impact -1.2% on reported revenue",
    "Backlog coverage at 3.2 months, up from 2.8",
]

_QUAL_DRIVERS = [
    "Strong demand across mid-market in the region",
    "Competitive pressure dampening pricing in core segment",
    "Customer consolidation creating larger but fewer deals",
    "Aftermarket attach rates improving with new service contracts",
    "Supply chain stabilization unlocking deferred orders",
    "Seasonal slowdown offset by strong project pipeline",
    "New product launches gaining traction in adjacent verticals",
    "Disciplined price realization holding above plan",
    "End-market recovery driving capex unlock",
    "Digital channels expanding direct-to-customer engagement",
]

_INTERNAL_FACTORS = [
    "New sales team fully onboarded and productive",
    "Capacity expansion completed; production +15%",
    "ERP migration causing temporary productivity dip",
    "Process improvement program delivering efficiency gains",
    "Key account manager transition in progress",
    "Training investment showing results in service quality",
    "Shared services consolidation reducing overhead allocation",
    "R&D pipeline maturing with three planned launches",
    "Reorg streamlining decision-making in front office",
    "Talent retention initiatives improving team stability",
]

_EXTERNAL_FACTORS = [
    "Market recovery in core sector accelerating",
    "Currency tailwinds supporting reported growth",
    "Raw material prices stabilizing after Q1 volatility",
    "Regulatory changes driving replacement demand",
    "Customer capex cycles shifting to H2 investment",
    "Geopolitical tensions affecting supply chain lead times",
    "Infrastructure spending creating in-region demand",
    "Competitive new entrant pricing aggressively in mid-market",
    "Energy transition driving demand in adjacent segments",
    "Interest rate environment slowing customer investment decisions",
]

_ONEOFF_EVENTS = [
    "Large one-time order from key account ($2.5M)",
    "Warranty claim settlement impacting margin (-$180K)",
    "",
    "Fleet replacement contract signed with strategic customer",
    "",
    "Insurance recovery from logistics incident (+$120K)",
    "",
    "",
    "Government grant for sustainability upgrade",
    "",
]

_PLANNED_ACTIONS = [
    "Expand aftermarket team by 2 FTE in Q2",
    "Launch new product line targeting mid-market",
    "Implement dynamic pricing tool for service contracts",
    "Accelerate digital service platform rollout",
    "Renegotiate key supplier contracts for better terms",
    "Intensify cross-selling between product lines",
    "Deploy predictive maintenance offering at top 10 accounts",
    "Establish local assembly capability to reduce lead times",
    "Run customer satisfaction survey and address gaps",
    "Optimize inventory levels via demand-sensing analytics",
]

_EXPECTED_IMPACT = [
    "Expected 3% uplift in service revenue by Q3",
    "Margin improvement of 0.5pp from cost optimization",
    "Pipeline growth of 15% from new market penetration",
    "Overhead reduction of $200K annually from shared services",
    "Customer retention rate target: 95%+ for FY",
    "Lead time reduction from 8 to 6 weeks by year-end",
    "Forecast accuracy target: 95% within 3 months",
    "OPEX ratio target: below 21% by Q4",
    "Revenue per FTE improvement of 8% YoY",
    "Working capital improvement via 5-day DSO reduction",
]

_SENTIMENT_TAGS = ["Positive", "Positive", "Neutral", "Cautious", "Positive", "Neutral", "Cautious", "Positive"]


def _generate_historical():
    """Generate monthly filled submissions for Jan 2025 - Jan 2026."""
    rows = []
    for dept in DEPARTMENTS:
        dept_id = dept["id"]
        dept_name = dept["name"]
        lead = dept["lead_name"]
        for month in _HISTORICAL_MONTHS:
            for kpi_def in KPI_DEFINITIONS:
                base = kpi_def["base_value"]
                var = kpi_def["variance"]
                value = round(base * _RNG.uniform(1 - var, 1 + var), 1)
                if kpi_def["unit"] == "days":
                    value = round(value)
                rows.append({
                    "department_id": dept_id,
                    "department_name": dept_name,
                    "kpi_name": kpi_def["name"],
                    "kpi_number": kpi_def["number"],
                    "kpi_category": kpi_def["category"],
                    "period": month,
                    "kpi_value": value,
                    "kpi_unit": kpi_def["unit"],
                    "key_drivers_quantitative": _RNG.choice(_QUANT_DRIVERS),
                    "key_drivers_qualitative": _RNG.choice(_QUAL_DRIVERS),
                    "internal_factors": _RNG.choice(_INTERNAL_FACTORS),
                    "external_factors": _RNG.choice(_EXTERNAL_FACTORS),
                    "oneoff_events": _RNG.choice(_ONEOFF_EVENTS),
                    "planned_actions": _RNG.choice(_PLANNED_ACTIONS),
                    "expected_impact": _RNG.choice(_EXPECTED_IMPACT),
                    "sentiment_tags": _RNG.choice(_SENTIMENT_TAGS),
                    "kpi_lockin": True,
                    "reviewed_by_gm": lead,
                    "submitted_by": lead,
                })
    return rows


def _generate_pending():
    """Generate partially-filled submissions for Feb 2026 + Mar 2026."""
    rows = []
    for dept in DEPARTMENTS:
        dept_id = dept["id"]
        dept_name = dept["name"]
        lead = dept["lead_name"]
        for month in ["Feb 2026", "Mar 2026"]:
            for kpi_def in KPI_DEFINITIONS:
                # Feb 2026: partially filled for North/Central, empty for others
                # Mar 2026: all empty (new month)
                is_filled = (
                    month == "Feb 2026"
                    and dept_name in ("Region North", "Region Central")
                    and kpi_def["number"] <= 3  # first 3 KPIs filled
                )
                base = kpi_def["base_value"]
                var = kpi_def["variance"]
                value = round(base * _RNG.uniform(1 - var, 1 + var), 1)
                if kpi_def["unit"] == "days":
                    value = round(value)
                rows.append({
                    "department_id": dept_id,
                    "department_name": dept_name,
                    "kpi_name": kpi_def["name"],
                    "kpi_number": kpi_def["number"],
                    "kpi_category": kpi_def["category"],
                    "period": month,
                    "kpi_value": value,
                    "kpi_unit": kpi_def["unit"],
                    "key_drivers_quantitative": _RNG.choice(_QUANT_DRIVERS) if is_filled else "",
                    "key_drivers_qualitative": _RNG.choice(_QUAL_DRIVERS) if is_filled else "",
                    "internal_factors": _RNG.choice(_INTERNAL_FACTORS) if is_filled else "",
                    "external_factors": _RNG.choice(_EXTERNAL_FACTORS) if is_filled else "",
                    "oneoff_events": _RNG.choice(_ONEOFF_EVENTS) if is_filled else "",
                    "planned_actions": _RNG.choice(_PLANNED_ACTIONS) if is_filled else "",
                    "expected_impact": _RNG.choice(_EXPECTED_IMPACT) if is_filled else "",
                    "sentiment_tags": _RNG.choice(_SENTIMENT_TAGS) if is_filled else "",
                    "kpi_lockin": False,
                    "reviewed_by_gm": lead if is_filled else "",
                    "submitted_by": lead,
                })
    return rows


# ---- Period date ranges ----

_PERIOD_MAP = {
    "Jan 2025": ("2025-01-01", "2025-01-31"),
    "Feb 2025": ("2025-02-01", "2025-02-28"),
    "Mar 2025": ("2025-03-01", "2025-03-31"),
    "Apr 2025": ("2025-04-01", "2025-04-30"),
    "May 2025": ("2025-05-01", "2025-05-31"),
    "Jun 2025": ("2025-06-01", "2025-06-30"),
    "Jul 2025": ("2025-07-01", "2025-07-31"),
    "Aug 2025": ("2025-08-01", "2025-08-31"),
    "Sep 2025": ("2025-09-01", "2025-09-30"),
    "Oct 2025": ("2025-10-01", "2025-10-31"),
    "Nov 2025": ("2025-11-01", "2025-11-30"),
    "Dec 2025": ("2025-12-01", "2025-12-31"),
    "Jan 2026": ("2026-01-01", "2026-01-31"),
    "Feb 2026": ("2026-02-01", "2026-02-28"),
    "Mar 2026": ("2026-03-01", "2026-03-31"),
}


def _build_submissions():
    raw = _generate_historical() + _generate_pending()
    subs = []
    for i, row in enumerate(raw):
        ps, pe = _PERIOD_MAP.get(row["period"], ("2025-01-01", "2025-01-31"))
        sub_id = f"s3000001-0000-0000-0000-{i + 1:012d}"
        subs.append({
            "id": sub_id,
            "department_id": row["department_id"],
            "department_name": row["department_name"],
            "kpi_name": row["kpi_name"],
            "kpi_number": row["kpi_number"],
            "kpi_category": row["kpi_category"],
            "period": row["period"],
            "period_start": ps,
            "kpi_value": row["kpi_value"],
            "kpi_unit": row["kpi_unit"],
            "period_end": pe,
            "key_drivers_quantitative": row["key_drivers_quantitative"],
            "key_drivers_qualitative": row["key_drivers_qualitative"],
            "internal_factors": row["internal_factors"],
            "external_factors": row["external_factors"],
            "oneoff_events": row["oneoff_events"],
            "planned_actions": row["planned_actions"],
            "expected_impact": row["expected_impact"],
            "sentiment_tags": row["sentiment_tags"],
            "kpi_lockin": row["kpi_lockin"],
            "reviewed_by_gm": row["reviewed_by_gm"],
            "submitted_by": row["submitted_by"],
            "submitted_at": f"2025-01-15T{10 + (i % 12):02d}:00:00",
            "updated_at": f"2025-01-15T{10 + (i % 12):02d}:00:00",
            "confluence_page_id": None,
            "confluence_page_url": None,
        })
    return subs


SUBMISSIONS = _build_submissions()


def _is_filled(sub: dict) -> bool:
    """Check if a submission has any qualitative fields filled in."""
    return any(
        sub.get(f)
        for f in (
            "key_drivers_quantitative", "key_drivers_qualitative",
            "internal_factors", "external_factors", "planned_actions",
            "expected_impact",
        )
    )


class MockLakebaseClient:
    """In-memory mock that mimics LakebaseClient for local dev."""

    def __init__(self):
        self._submissions = list(SUBMISSIONS)

    # --- Userbase ---

    def get_userbase_entry(self, email: str) -> dict | None:
        # Mock: return first regional lead for any email
        return {
            "employee_business_email": email,
            "employee_name": "Alex Morgan",
            "department_name": "Region North",
            "operation_unit_code": "REGN",
            "job_name": "General Manager",
        }

    # --- Departments ---

    def get_departments(self) -> list[dict]:
        return sorted(DEPARTMENTS, key=lambda d: d["name"])

    def get_department(self, dept_id: str) -> dict | None:
        return next((d for d in DEPARTMENTS if d["id"] == dept_id), None)

    # --- Submissions ---

    def get_submissions(
        self,
        department_id: str | None = None,
        period: str | None = None,
    ) -> list[dict]:
        result = list(self._submissions)
        if department_id:
            result = [s for s in result if s["department_id"] == department_id]
        if period:
            result = [s for s in result if s["period"] == period]
        return sorted(result, key=lambda s: (s["period"], s["kpi_number"]))

    def get_submission(self, sub_id: str) -> dict | None:
        return next((s for s in self._submissions if s["id"] == sub_id), None)

    def update_submission(self, sub_id: str, data: dict) -> dict | None:
        sub = self.get_submission(sub_id)
        if not sub:
            return None
        sub.update(data)
        sub["updated_at"] = datetime.now().isoformat()
        return sub

    def update_submission_confluence(self, sub_id: str, page_id: str, page_url: str) -> dict | None:
        sub = self.get_submission(sub_id)
        if not sub:
            return None
        sub["confluence_page_id"] = page_id
        sub["confluence_page_url"] = page_url
        sub["updated_at"] = datetime.now().isoformat()
        return sub

    # --- Dashboard ---

    def get_dashboard_summary(self, period: str | None = None) -> dict:
        subs = self.get_submissions(period=period)
        total = len(subs)
        if total == 0:
            return {"total_entries": 0, "filled_entries": 0, "locked_entries": 0, "gm_reviewed_entries": 0, "departments_reporting": 0}

        filled = sum(1 for s in subs if _is_filled(s))
        locked = sum(1 for s in subs if s["kpi_lockin"])
        gm_reviewed = sum(1 for s in subs if s["reviewed_by_gm"])
        departments_reporting = len(set(s["department_id"] for s in subs if _is_filled(s)))

        return {
            "total_entries": total,
            "filled_entries": filled,
            "locked_entries": locked,
            "gm_reviewed_entries": gm_reviewed,
            "departments_reporting": departments_reporting,
        }

    def get_department_detail(self, dept_id: str, period: str | None = None) -> dict | None:
        dept = self.get_department(dept_id)
        if not dept:
            return None

        subs = self.get_submissions(department_id=dept_id, period=period)
        total = len(subs)
        filled = sum(1 for s in subs if _is_filled(s))
        locked = sum(1 for s in subs if s["kpi_lockin"])
        fill_rate = round((filled / total) * 100, 1) if total > 0 else 0
        lock_rate = round((locked / total) * 100, 1) if total > 0 else 0

        return {
            "department": dept,
            "submissions": subs,
            "fill_rate": fill_rate,
            "lock_rate": lock_rate,
            "kpi_count": total,
        }
