# Financial KPI Reporting — Reference Implementation

## The Problem

Finance teams across multi-region enterprises struggle with **scattered, manual KPI reporting**. Regional leads track actuals in spreadsheets, CFOs can't get real-time visibility, and nobody has a single source of truth for financial performance.

## The Solution

A **governed, web-based KPI reporting platform** that combines structured submission workflows with AI-powered analytics and executive dashboards — all built on Databricks.

### Two Personas, One Experience

| Regional Lead | Chief Financial Officer |
|---|---|
| ✓ Submit monthly KPIs with targets pre-loaded | ✓ View consolidated performance across all regions |
| ✓ Provide justifications for actuals | ✓ Drill into underperforming areas in real-time |
| ✓ Lock submissions once reviewed | ✓ Ask ad-hoc questions via AI (Genie) |
| ✓ Track submission status | ✓ Publish executive summary to Confluence |

## Key Capabilities

- **Structured submission workflow** — KPIs follow a simple lifecycle: Pending Review → Reviewed → Published
- **Real-time executive dashboard** — Health score, regional performance, achievement trends, and drill-downs
- **AI-powered analytics** — Databricks Genie translates natural-language questions into SQL queries over live KPI data
- **Automated publishing** — Idempotent integration with Confluence for audit trail and stakeholder distribution
- **Operational reminders** — Scheduled job nudges regional leads for unjustified KPIs
- **Transactional + analytical layers** — Lakebase for structured submissions, Unity Catalog Delta for Genie access

## Architecture

```
React Frontend (Dashboard + Submission)
    ↓ (REST API)
FastAPI Backend (Business Logic)
    ├─ Lakebase (PostgreSQL) — Transactional submissions
    ├─ Genie Space — AI-powered Q&A
    ├─ Confluence (optional) — Publishing
    └─ Unity Catalog — Analytical views (Lakebase CDF)
```

**Tech Stack:**
- **Frontend:** React 19, TanStack Router, Recharts, Tailwind
- **Backend:** FastAPI, SQLAlchemy, Pydantic
- **Data Layer:** Lakebase Autoscale (transactional), Delta + UC (analytical)
- **AI:** Databricks Genie
- **Deployment:** Databricks Apps, Asset Bundles

## What Makes It Reference-Grade

✓ **End-to-end pattern** — Shows how Apps, Lakebase, Genie, and UC work together  
✓ **Production-ready foundation** — Security, access control, and customization guidance  
✓ **Guided deployment** — Notebooks walk through Lakebase setup, Lakebase CDF, and Apps deployment  
✓ **Local dev support** — Full UI testing without Databricks resources via in-memory mock  
✓ **Multi-persona UX** — Demonstrates role-based workflows in a real business context  

## Use Cases

- **Financial planning** — Replace spreadsheet-based regional reporting with a web app
- **Sales/ops reviews** — Dashboard drill-downs into underperforming regions
- **Compliance & audit** — Formal publishing trail in Confluence + Lakebase CDF
- **Scaling governance** — Template for other reporting workflows (budgets, forecasts, headcount)

## Getting Started

1. **Clone the repo** — `git clone https://github.com/databricks-solutions/...`
2. **Deploy locally** — `uv sync && bun install && uv run apx dev` (no Databricks resources needed for UI testing)
3. **Deploy to Databricks** — Clone as a Databricks Git folder and run the `notebooks/01_setup_lakebase.py` walkthrough (notebook 03 builds + deploys the App — no `bundle deploy` needed)
4. **Customize** — Swap departments, KPIs, and publishing target for your organization

## Learn More

- **README:** Full architecture, deployment guide, and customization patterns
- **DESIGN.md:** Data model, personas, and integration points
- **Notebooks:** Step-by-step deployment walkthrough (01 Lakebase → 02 Lakebase CDF → 03 Apps deploy)
- **GitHub:** [Link to repository]

---

**Built by Databricks Field Engineering**  
Reference Implementation — Synthetic Data Only  
[License: Apache 2.0](LICENSE)

