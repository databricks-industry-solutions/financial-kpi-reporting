# Financial KPI Reporting Application - Design Overview

## Purpose

A web application that centralizes financial KPI reporting across global Regions. It replaces manual spreadsheet-based reporting with a structured submission, review, and publishing workflow - giving regional leads a clear process and executives real-time visibility into financial performance.

## Users & Personas

| Persona | Role | What they do in the app |
|---|---|---|
| **Regional Lead** | Regional finance owner | Submits KPI actuals, provides justifications, reviews and publishes results |
| **Chief Financial Officer** | Executive oversight | Monitors performance across all regions, drills into underperforming areas, asks ad-hoc questions via AI |

## Core Capabilities

### 1. KPI Submission & Review

- Regional Leads see their KPIs with targets pre-loaded for each reporting period
- For each KPI, they enter the actual value and a written justification explaining the result
- Submissions follow a simple lifecycle: **Pending Review** → **Reviewed** → **Published**
- Published KPIs are automatically pushed to Confluence as formal documentation

### 2. Executive Dashboard

- Four headline metrics: Health Score, Total Submissions, Average Achievement, Regions Reporting
- A grid of all Regions, color-coded by performance status (On Track / At Risk / Behind)
- Click any region to drill down into individual KPIs with charts showing target vs actual and achievement trends over time
- One-click export of the executive summary to Confluence

### 3. AI-Powered Analysis (Databricks Genie)

- A natural language chat interface embedded in the dashboard
- Executives can ask questions like "Which region had the highest revenue growth last quarter?" or "Show KPIs below 90% achievement"
- Genie translates questions into SQL, executes against the KPI data, and returns results with tables and context

## Data Model

| Concept | Description |
|---|---|
| **Regions** | Organizational units (e.g. geographic regions or business units) with an assigned lead |
| **KPI Categories** | Groupings such as Revenue, Profitability, Working Capital, Cost Control, Cash Flow, Compliance |
| **KPI Submissions** | The core data: a specific KPI for a specific region and period, with target value, actual value, trend, justification, and review status |

## Architecture

```
┌────────────────────────────────┐
│       React Frontend           │
│  (Dashboard, Submission UI)    │
└──────────────┬─────────────────┘
               │ REST API
┌──────────────┴─────────────────┐
│       FastAPI Backend          │
│  (Business logic, auth proxy)  │
├────────┬───────────┬───────────┤
│        │           │           │
▼        ▼           ▼           │
Lakebase   Confluence   Genie    │
(Postgres)  (Wiki)    (AI/BI)    │
└────────┴───────────┴───────────┘
```

| Component | Technology | Purpose |
|---|---|---|
| **Frontend** | React, TanStack Router, Recharts | Interactive UI with filtering, charts, and real-time data |
| **Backend** | Python / FastAPI | API layer, business logic, credential management |
| **Database** | Databricks Lakebase (managed PostgreSQL) | Structured storage for KPIs, departments, and categories |
| **Documentation** | Confluence REST API | Automated publishing of KPI reports and executive summaries |
| **AI Analysis** | Databricks Genie | Natural language querying of KPI data |

## Integration Points

- **Lakebase** serves as the transactional database, handling reads and writes for all KPI data. Authentication is handled server-side via Databricks service principals.
- **Confluence** acts as the audit trail and distribution channel. Reports are created or updated automatically (idempotent by title), organized under a configurable parent page.
- **Genie** provides AI-powered analytics. The backend proxies all requests, keeping API credentials off the client. Multi-turn conversations are supported so users can ask follow-up questions.

## Deployment

The application is packaged and deployed as a **Databricks App** using Asset Bundles, providing:

- Managed hosting within the Databricks workspace
- Built-in authentication and access control
- Simple promotion across environments (dev → staging → production)

A scheduled alert job sends daily reminders for KPIs still awaiting justification.

## What's Customizable

This is a reference implementation. In a production deployment, you would typically adapt:

- **Organizational structure** — map to your own divisions, business units, or cost centers
- **KPI definitions** — define the specific metrics, targets, and reporting cadence relevant to your business
- **Submission workflow** — add approval chains, notifications, or multi-level review as needed
- **Publishing target** — Confluence is one option; could be SharePoint, email, or any documentation system
- **Access control** — role-based visibility so each lead sees only their region's data
- **AI context** — configure Genie with your own data model and business glossary for accurate natural language queries
