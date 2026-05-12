# Databricks notebook source
# MAGIC %md
# MAGIC # Financial KPI Reporting — Deploy Guide (Step 1: Lakebase)
# MAGIC
# MAGIC This is the canonical deploy walkthrough. Run this notebook top-to-bottom,
# MAGIC then follow the steps in the "Next steps" sections at the bottom.
# MAGIC
# MAGIC ## Deploy roadmap
# MAGIC
# MAGIC | # | Step | Where it happens | Required? |
# MAGIC |---|------|------------------|-----------|
# MAGIC | 1 | **Provision Lakebase + seed data** | this notebook | yes |
# MAGIC | 2 | **Activate Lakehouse Sync** | `notebooks/02_setup_forward_etl.py` + UI | yes (creates the Delta tables Genie reads) |
# MAGIC | 3 | **Genie Space + Confluence + App deploy** | `notebooks/03_deploy_app.py` (guided checklist) | yes |
# MAGIC
# MAGIC > **Order matters**: Lakehouse Sync (notebook 02) must run before the Genie
# MAGIC > Space step in notebook 03 — the workspace UI requires at least one table
# MAGIC > to be selected when you create a Space, so the Delta tables need to exist first.
# MAGIC
# MAGIC ## Prerequisites
# MAGIC
# MAGIC - Databricks workspace with **Apps**, **Lakebase**, and **Genie Spaces** enabled
# MAGIC - Permission to:
# MAGIC   - Create Lakebase projects (`postgres.projects.create`)
# MAGIC   - Create Unity Catalog schemas in your target catalog
# MAGIC   - Create Apps and attach resources
# MAGIC - *(Optional, only if you want the publish-to-wiki feature)* a Confluence
# MAGIC   Cloud space + an account that can mint API tokens
# MAGIC - On your laptop, before running these notebooks: Databricks CLI configured
# MAGIC   (`databricks auth login`) and `databricks bundle deploy` already run once
# MAGIC   so the source code is in the workspace. (Local dev uses Python 3.11+,
# MAGIC   [uv](https://docs.astral.sh/uv/), Node 20+, and Bun — see the README.)
# MAGIC
# MAGIC ## What this notebook does
# MAGIC
# MAGIC Creates a Lakebase Autoscale project (default name `kpi-reporting`),
# MAGIC initializes the `departments`, `monthly_reporting_userbase`, and
# MAGIC `kpi_submissions` tables (matching the application's runtime schema),
# MAGIC and seeds realistic synthetic data. Idempotent — safe to re-run.
# MAGIC
# MAGIC The widget below lets you change the project name if `kpi-reporting`
# MAGIC is taken in your workspace.

# COMMAND ----------

# MAGIC %pip install -U "psycopg[binary]>=3.0"
# MAGIC dbutils.library.restartPython()

# COMMAND ----------

import requests
import time
import uuid
import random
from datetime import datetime
import psycopg

# Create widgets — adjust their values via the toolbar at the top of the notebook
dbutils.widgets.text("lakebase_project", "kpi-reporting", "Lakebase project ID")
dbutils.widgets.text("lakebase_display_name", "Financial KPI Reporting", "Lakebase display name")

# COMMAND ----------

# Read widget values
LAKEBASE_PROJECT_ID = dbutils.widgets.get("lakebase_project").strip()
LAKEBASE_DISPLAY_NAME = dbutils.widgets.get("lakebase_display_name").strip()
print(f"Project ID:   {LAKEBASE_PROJECT_ID}")
print(f"Display name: {LAKEBASE_DISPLAY_NAME}")

# COMMAND ----------

# Get workspace URL and token for REST API
ctx = dbutils.notebook.entry_point.getDbutils().notebook().getContext()
host = ctx.apiUrl().get()
token = ctx.apiToken().get()
headers = {
    "Authorization": f"Bearer {token}",
    "Content-Type": "application/json"
}

print(f"Workspace: {host}")

# COMMAND ----------

# MAGIC %md
# MAGIC ## Create or Get Lakebase Autoscale Project

# COMMAND ----------

project_resp = requests.get(
    f"{host}/api/2.0/postgres/projects/{LAKEBASE_PROJECT_ID}",
    headers=headers
)

if project_resp.status_code == 200:
    print(f"Lakebase project already exists: {LAKEBASE_PROJECT_ID}")
else:
    create_resp = requests.post(
        f"{host}/api/2.0/postgres/projects",
        headers=headers,
        params={"project_id": LAKEBASE_PROJECT_ID},
        json={"spec": {"display_name": LAKEBASE_DISPLAY_NAME, "pg_version": "17"}}
    )
    if create_resp.status_code in (200, 201):
        print(f"Created Lakebase project: {LAKEBASE_PROJECT_ID}")
        op_name = create_resp.json().get("name", "")
        if op_name:
            for _ in range(120):
                op_resp = requests.get(f"{host}/api/2.0/{op_name}", headers=headers)
                if op_resp.status_code == 200 and op_resp.json().get("done", False):
                    print("Project creation completed")
                    break
                time.sleep(10)
    else:
        raise Exception(f"Failed to create Lakebase project: {create_resp.text}")

# COMMAND ----------

# MAGIC %md
# MAGIC ## Wait for Compute Endpoint

# COMMAND ----------

endpoint_path = f"projects/{LAKEBASE_PROJECT_ID}/branches/production/endpoints/primary"

for _ in range(60):
    ep_resp = requests.get(f"{host}/api/2.0/postgres/{endpoint_path}", headers=headers)
    if ep_resp.status_code == 200:
        state = ep_resp.json().get("status", {}).get("current_state", "UNKNOWN")
        print(f"Endpoint state: {state}")
        if state == "ACTIVE":
            break
    time.sleep(15)
else:
    print("Warning: Endpoint did not reach ACTIVE within 15 minutes, continuing anyway")

# COMMAND ----------

# MAGIC %md
# MAGIC ## Connection Info

# COMMAND ----------

ep_resp = requests.get(f"{host}/api/2.0/postgres/{endpoint_path}", headers=headers)
pg_host = ep_resp.json()["status"]["hosts"]["host"]

cred_resp = requests.post(
    f"{host}/api/2.0/postgres/credentials",
    headers=headers,
    json={"endpoint": endpoint_path}
)
pg_token = cred_resp.json()["token"]

me_resp = requests.get(f"{host}/api/2.0/preview/scim/v2/Me", headers=headers)
username = me_resp.json().get("userName", "unknown")

print(f"Host: {pg_host}")
print(f"User: {username}")

conn_string = (
    f"host={pg_host} dbname=databricks_postgres user={username} "
    f"password={pg_token} sslmode=require"
)

# COMMAND ----------

# MAGIC %md
# MAGIC ## Create Tables
# MAGIC
# MAGIC Schema matches the application runtime (`src/kpi_reporting/backend/lakebase.py`
# MAGIC and `models.py`). Key design points:
# MAGIC - `departments`: regions with an assigned lead
# MAGIC - `monthly_reporting_userbase`: maps a workspace identity (email) to a region + role
# MAGIC - `kpi_submissions`: one row per (region, KPI, period) with the qualitative
# MAGIC   commentary fields the app exposes for editing

# COMMAND ----------

with psycopg.connect(conn_string) as conn:
    conn.autocommit = True
    with conn.cursor() as cur:
        cur.execute("""
            CREATE TABLE IF NOT EXISTS departments (
                id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
                name VARCHAR(200) NOT NULL UNIQUE,
                lead_name VARCHAR(200) NOT NULL,
                created_at TIMESTAMP NOT NULL DEFAULT NOW()
            )
        """)
        print("Created departments table")

        cur.execute("""
            CREATE TABLE IF NOT EXISTS monthly_reporting_userbase (
                employee_business_email VARCHAR(200) PRIMARY KEY,
                employee_name VARCHAR(200) NOT NULL,
                department_name VARCHAR(200) NOT NULL,
                operation_unit_code VARCHAR(50) NOT NULL DEFAULT '',
                job_name VARCHAR(100) NOT NULL DEFAULT ''
            )
        """)
        print("Created monthly_reporting_userbase table")

        cur.execute("""
            CREATE TABLE IF NOT EXISTS kpi_submissions (
                id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
                department_id UUID NOT NULL REFERENCES departments(id),
                department_name VARCHAR(200) NOT NULL,
                kpi_name VARCHAR(300) NOT NULL,
                kpi_number INT NOT NULL,
                kpi_category VARCHAR(100) NOT NULL,
                period VARCHAR(20) NOT NULL,
                period_start DATE NOT NULL,
                period_end DATE NOT NULL,
                kpi_value DOUBLE PRECISION,
                kpi_unit VARCHAR(20) NOT NULL DEFAULT '',
                key_drivers_quantitative TEXT NOT NULL DEFAULT '',
                key_drivers_qualitative TEXT NOT NULL DEFAULT '',
                internal_factors TEXT NOT NULL DEFAULT '',
                external_factors TEXT NOT NULL DEFAULT '',
                oneoff_events TEXT NOT NULL DEFAULT '',
                planned_actions TEXT NOT NULL DEFAULT '',
                expected_impact TEXT NOT NULL DEFAULT '',
                sentiment_tags VARCHAR(100) NOT NULL DEFAULT '',
                kpi_lockin BOOLEAN NOT NULL DEFAULT FALSE,
                reviewed_by_gm VARCHAR(200) NOT NULL DEFAULT '',
                submitted_by VARCHAR(200) NOT NULL DEFAULT '',
                submitted_at TIMESTAMP NOT NULL DEFAULT NOW(),
                updated_at TIMESTAMP NOT NULL DEFAULT NOW(),
                confluence_page_id VARCHAR(100),
                confluence_page_url VARCHAR(500),
                UNIQUE (department_id, kpi_number, period)
            )
        """)
        print("Created kpi_submissions table")

# COMMAND ----------

# MAGIC %md
# MAGIC ## Seed Departments and Userbase

# COMMAND ----------

# 6 regions, matching the mock-data layer
DEPARTMENTS = [
    ("Region North", "Alex Morgan"),
    ("Region South", "Priya Patel"),
    ("Region East", "Jin Park"),
    ("Region West", "Marcus Hill"),
    ("Region Central", "Sofia Lopez"),
    ("Region International", "Noah Schmidt"),
]

# Userbase entries: regional leads (gm) + one executive (CFO)
# Replace the email values below with the workspace identities that should
# be granted access in your environment.
USERBASE = [
    ("alex.morgan@example.com",   "Alex Morgan",   "Region North",         "REGN", "General Manager"),
    ("priya.patel@example.com",   "Priya Patel",   "Region South",         "REGS", "General Manager"),
    ("jin.park@example.com",      "Jin Park",      "Region East",          "REGE", "General Manager"),
    ("marcus.hill@example.com",   "Marcus Hill",   "Region West",          "REGW", "General Manager"),
    ("sofia.lopez@example.com",   "Sofia Lopez",   "Region Central",       "REGC", "General Manager"),
    ("noah.schmidt@example.com",  "Noah Schmidt",  "Region International", "REGI", "General Manager"),
    ("sam.carter@example.com",    "Sam Carter",    "Region North",         "CFO",  "Chief Financial Officer"),
]

dept_ids = {}
with psycopg.connect(conn_string) as conn:
    conn.autocommit = True
    with conn.cursor() as cur:
        for name, lead in DEPARTMENTS:
            cur.execute(
                """INSERT INTO departments (id, name, lead_name) VALUES (%s, %s, %s)
                   ON CONFLICT (name) DO UPDATE SET lead_name = EXCLUDED.lead_name
                   RETURNING id""",
                (str(uuid.uuid4()), name, lead),
            )
            dept_ids[name] = str(cur.fetchone()[0])
        print(f"Seeded {len(dept_ids)} departments")

        for email, name, dept, opcode, job in USERBASE:
            cur.execute(
                """INSERT INTO monthly_reporting_userbase
                       (employee_business_email, employee_name, department_name, operation_unit_code, job_name)
                   VALUES (%s, %s, %s, %s, %s)
                   ON CONFLICT (employee_business_email) DO UPDATE SET
                       employee_name = EXCLUDED.employee_name,
                       department_name = EXCLUDED.department_name,
                       operation_unit_code = EXCLUDED.operation_unit_code,
                       job_name = EXCLUDED.job_name""",
                (email, name, dept, opcode, job),
            )
        print(f"Seeded {len(USERBASE)} userbase entries")

# COMMAND ----------

# MAGIC %md
# MAGIC ## Seed KPI Submissions
# MAGIC
# MAGIC Generates 13 historical (locked + reviewed) months and 2 in-progress months
# MAGIC for each (region × KPI) combination. Mirrors `mock_data.py` so local dev
# MAGIC and Lakebase look identical.

# COMMAND ----------

KPI_DEFINITIONS = [
    # (name, number, category, base_value, unit, variance)
    ("Revenue Growth",   1, "Revenue",         8.5,     "%",    0.18),
    ("Operating Margin", 2, "Profitability",   14.0,    "%",    0.10),
    ("DSO",              3, "Working Capital", 52,      "days", 0.12),
    ("OPEX Ratio",       4, "Cost Control",    22.0,    "%",    0.08),
    ("Free Cash Flow",   5, "Cash Flow",       4200000, "USD",  0.20),
]

PERIODS = [
    ("Jan 2025", "2025-01-01", "2025-01-31"),
    ("Feb 2025", "2025-02-01", "2025-02-28"),
    ("Mar 2025", "2025-03-01", "2025-03-31"),
    ("Apr 2025", "2025-04-01", "2025-04-30"),
    ("May 2025", "2025-05-01", "2025-05-31"),
    ("Jun 2025", "2025-06-01", "2025-06-30"),
    ("Jul 2025", "2025-07-01", "2025-07-31"),
    ("Aug 2025", "2025-08-01", "2025-08-31"),
    ("Sep 2025", "2025-09-01", "2025-09-30"),
    ("Oct 2025", "2025-10-01", "2025-10-31"),
    ("Nov 2025", "2025-11-01", "2025-11-30"),
    ("Dec 2025", "2025-12-01", "2025-12-31"),
    ("Jan 2026", "2026-01-01", "2026-01-31"),
    ("Feb 2026", "2026-02-01", "2026-02-28"),  # in progress
    ("Mar 2026", "2026-03-01", "2026-03-31"),  # in progress
]
HISTORICAL_PERIODS = {p[0] for p in PERIODS[:13]}

QUANT_DRIVERS = [
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
QUAL_DRIVERS = [
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
INTERNAL_FACTORS = [
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
EXTERNAL_FACTORS = [
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
ONEOFF_EVENTS = [
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
PLANNED_ACTIONS = [
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
EXPECTED_IMPACT = [
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
SENTIMENT_TAGS = ["Positive", "Positive", "Neutral", "Cautious", "Positive", "Neutral", "Cautious", "Positive"]

random.seed(42)

def fill_or_blank(value, filled):
    return value if filled else ""

records = []
for dept_name, lead in DEPARTMENTS:
    for period_name, p_start, p_end in PERIODS:
        is_historical = period_name in HISTORICAL_PERIODS
        # In-progress demo: Region North + Central, Feb 2026, first 3 KPIs filled
        is_in_progress_filled = (
            period_name == "Feb 2026"
            and dept_name in ("Region North", "Region Central")
        )

        for kpi_name, kpi_num, category, base, unit, var in KPI_DEFINITIONS:
            value = round(base * random.uniform(1 - var, 1 + var), 1)
            if unit == "days":
                value = round(value)

            kpi_filled = is_historical or (is_in_progress_filled and kpi_num <= 3)

            records.append({
                "id": str(uuid.uuid4()),
                "department_id": dept_ids[dept_name],
                "department_name": dept_name,
                "kpi_name": kpi_name,
                "kpi_number": kpi_num,
                "kpi_category": category,
                "period": period_name,
                "period_start": p_start,
                "period_end": p_end,
                "kpi_value": value,
                "kpi_unit": unit,
                "key_drivers_quantitative": fill_or_blank(random.choice(QUANT_DRIVERS), kpi_filled),
                "key_drivers_qualitative":  fill_or_blank(random.choice(QUAL_DRIVERS), kpi_filled),
                "internal_factors":         fill_or_blank(random.choice(INTERNAL_FACTORS), kpi_filled),
                "external_factors":         fill_or_blank(random.choice(EXTERNAL_FACTORS), kpi_filled),
                "oneoff_events":            fill_or_blank(random.choice(ONEOFF_EVENTS), kpi_filled),
                "planned_actions":          fill_or_blank(random.choice(PLANNED_ACTIONS), kpi_filled),
                "expected_impact":          fill_or_blank(random.choice(EXPECTED_IMPACT), kpi_filled),
                "sentiment_tags":           fill_or_blank(random.choice(SENTIMENT_TAGS), kpi_filled),
                "kpi_lockin":               is_historical,
                "reviewed_by_gm":           lead if is_historical else "",
                "submitted_by":             lead,
            })

print(f"Generated {len(records)} KPI submission records")

# COMMAND ----------

# MAGIC %md
# MAGIC ## Insert Submissions

# COMMAND ----------

INSERT_SQL = """
INSERT INTO kpi_submissions (
    id, department_id, department_name, kpi_name, kpi_number, kpi_category,
    period, period_start, period_end, kpi_value, kpi_unit,
    key_drivers_quantitative, key_drivers_qualitative,
    internal_factors, external_factors, oneoff_events,
    planned_actions, expected_impact, sentiment_tags,
    kpi_lockin, reviewed_by_gm, submitted_by
) VALUES (
    %(id)s, %(department_id)s, %(department_name)s, %(kpi_name)s, %(kpi_number)s, %(kpi_category)s,
    %(period)s, %(period_start)s, %(period_end)s, %(kpi_value)s, %(kpi_unit)s,
    %(key_drivers_quantitative)s, %(key_drivers_qualitative)s,
    %(internal_factors)s, %(external_factors)s, %(oneoff_events)s,
    %(planned_actions)s, %(expected_impact)s, %(sentiment_tags)s,
    %(kpi_lockin)s, %(reviewed_by_gm)s, %(submitted_by)s
)
ON CONFLICT (department_id, kpi_number, period) DO NOTHING
"""

with psycopg.connect(conn_string) as conn:
    conn.autocommit = True
    with conn.cursor() as cur:
        for rec in records:
            cur.execute(INSERT_SQL, rec)
        print(f"Inserted up to {len(records)} KPI submissions")

# COMMAND ----------

# MAGIC %md
# MAGIC ## Verify

# COMMAND ----------

with psycopg.connect(conn_string) as conn:
    with conn.cursor() as cur:
        cur.execute("SELECT COUNT(*) FROM departments")
        print(f"Departments: {cur.fetchone()[0]}")

        cur.execute("SELECT COUNT(*) FROM monthly_reporting_userbase")
        print(f"Userbase entries: {cur.fetchone()[0]}")

        cur.execute("SELECT COUNT(*) FROM kpi_submissions")
        print(f"Total submissions: {cur.fetchone()[0]}")

        cur.execute("""
            SELECT period, COUNT(*) FILTER (WHERE kpi_lockin) AS locked, COUNT(*) AS total
            FROM kpi_submissions GROUP BY period ORDER BY MIN(period_start)
        """)
        for period, locked, total in cur.fetchall():
            print(f"  {period}: {locked}/{total} locked")

# COMMAND ----------

displayHTML(f"""
<div style="padding: 20px; background-color: #e8f8e8; border-radius: 8px; border-left: 4px solid #00cc66;">
    <h2 style="color: #00cc66; margin-top: 0;">Step 1 done — Lakebase ready</h2>
    <p><strong>Project:</strong> {LAKEBASE_PROJECT_ID}</p>
    <p><strong>Tables:</strong> departments, monthly_reporting_userbase, kpi_submissions</p>
    <p><strong>Regions:</strong> {len(DEPARTMENTS)}</p>
    <p><strong>KPIs per region:</strong> {len(KPI_DEFINITIONS)}</p>
    <p><strong>Periods:</strong> {len(PERIODS)} ({len(HISTORICAL_PERIODS)} historical, {len(PERIODS) - len(HISTORICAL_PERIODS)} in progress)</p>
    <p><strong>Submissions:</strong> {len(records)}</p>
    <p style="margin-top: 12px;">Continue to <strong>Step 2</strong> below.</p>
</div>
""")

# COMMAND ----------

# MAGIC %md
# MAGIC ## Step 2 — Activate Lakehouse Sync
# MAGIC
# MAGIC Open **`notebooks/02_setup_forward_etl.py`**. At the top, the notebook has
# MAGIC widgets for **Target catalog** and **Target schema** — pick a catalog you
# MAGIC have write access to (default `main`) and any schema name (default
# MAGIC `kpi_reporting`). The schema is created for you if it doesn't exist.
# MAGIC
# MAGIC The notebook then:
# MAGIC
# MAGIC 1. Sets `REPLICA IDENTITY FULL` on the source tables (required for CDC)
# MAGIC 2. Creates the destination schema in your chosen catalog
# MAGIC 3. Renders the exact values to plug into the Lakehouse Sync UI
# MAGIC 4. Verifies sync activation and creates clean views the Genie Space reads
# MAGIC
# MAGIC When notebook 02 finishes you'll have these tables in Unity Catalog
# MAGIC (substitute your catalog and schema for `<catalog>.<schema>`):
# MAGIC - `<catalog>.<schema>.departments`
# MAGIC - `<catalog>.<schema>.monthly_reporting_userbase`
# MAGIC - `<catalog>.<schema>.kpi_submissions`
# MAGIC
# MAGIC Note the catalog and schema you picked — you'll need them in notebook 03.

# COMMAND ----------

# MAGIC %md
# MAGIC ## Step 3 — Genie Space, Confluence, App deploy
# MAGIC
# MAGIC Open **`notebooks/03_deploy_app.py`**. It's a guided checklist that walks
# MAGIC you through:
# MAGIC
# MAGIC - Creating the Genie Space and adding the right tables / instructions
# MAGIC - Generating a Confluence API token + storing it as a Databricks secret
# MAGIC - Creating the App and attaching the Lakebase / Genie / secret resources
# MAGIC - Running `databricks bundle deploy` + `databricks apps deploy` from your laptop
# MAGIC - Smoke-testing the running app
# MAGIC
# MAGIC A troubleshooting matrix is at the bottom of that notebook for the
# MAGIC most common failure modes.
