# Databricks notebook source
# MAGIC %md
# MAGIC # Justification Reminder
# MAGIC
# MAGIC Finds KPI submissions that are still missing their written justification (or
# MAGIC haven't been locked in yet) and renders a per-region reminder for the
# MAGIC responsible lead.
# MAGIC
# MAGIC A KPI counts as **outstanding** when either:
# MAGIC - `key_drivers_quantitative` is still blank (no justification written), or
# MAGIC - `kpi_lockin` is FALSE (the lead hasn't formally submitted it)
# MAGIC
# MAGIC **Prerequisite:** notebook 01 (Lakebase project + seeded tables).
# MAGIC
# MAGIC **Scheduling:** attach this notebook to a Databricks Job to run it on a
# MAGIC cadence (e.g. daily while a reporting period is open). The reminders print to
# MAGIC the notebook output and are returned as JSON via `dbutils.notebook.exit`, so a
# MAGIC downstream task can forward them to email or Slack.

# COMMAND ----------

# MAGIC %pip install -U "databricks-sdk>=0.123.0" "psycopg[binary]>=3.0"
# MAGIC dbutils.library.restartPython()

# COMMAND ----------

import json
from collections import defaultdict

import psycopg
from databricks.sdk import WorkspaceClient

# COMMAND ----------

dbutils.widgets.text("lakebase_project", "kpi-reporting", "Lakebase project ID")
dbutils.widgets.text("app_name", "kpi-reporting", "App name (for the reminder deep link)")
dbutils.widgets.text("period", "", "Reporting period to check, e.g. 'Mar 2026' (blank = the latest period present)")

# COMMAND ----------

LAKEBASE_PROJECT_ID = dbutils.widgets.get("lakebase_project").strip()
APP_NAME = dbutils.widgets.get("app_name").strip()
PERIOD = dbutils.widgets.get("period").strip()

w = WorkspaceClient()

print(f"Lakebase project: {LAKEBASE_PROJECT_ID}")
print(f"App name:         {APP_NAME}")
print(f"Period:           {PERIOD or '(latest period in the data)'}")

# COMMAND ----------

# MAGIC %md
# MAGIC ## Connect to Lakebase
# MAGIC
# MAGIC Same connection pattern as notebooks 01 and 02: resolve the endpoint host,
# MAGIC mint a short-lived OAuth credential, and connect as the current user.

# COMMAND ----------

_branch = f"projects/{LAKEBASE_PROJECT_ID}/branches/production"
_endpoint = f"{_branch}/endpoints/primary"

endpoint = w.postgres.get_endpoint(name=_endpoint)
pg_host = endpoint.status.hosts.host

cred = w.postgres.generate_database_credential(endpoint=_endpoint)
pg_token = cred.token

username = w.current_user.me().user_name

conn_string = (
    f"host={pg_host} dbname=databricks_postgres "
    f"user={username} password={pg_token} sslmode=require"
)
print(f"Connected to Lakebase: {pg_host}")

# COMMAND ----------

# MAGIC %md
# MAGIC ## Resolve the app URL for the reminder deep link

# COMMAND ----------

_app_url = ""
try:
    _app = w.apps.get(name=APP_NAME)
    _app_url = (_app.url or "").rstrip("/")
except Exception as e:
    print(f"Could not look up app '{APP_NAME}' ({e}) — reminders will omit the link.")

SUBMISSION_URL = f"{_app_url}/kpi-submission" if _app_url else "(app URL unavailable)"
print(f"Reminder link: {SUBMISSION_URL}")

# COMMAND ----------

# MAGIC %md
# MAGIC ## Query outstanding justifications

# COMMAND ----------

# Only the target period. When the widget is blank, use the most recent period
# present in the table (ordered by period_start, not the display string).
QUERY = """
    SELECT
        s.department_name,
        d.lead_name,
        s.kpi_name,
        s.kpi_number,
        s.period,
        s.kpi_value,
        s.kpi_unit,
        s.kpi_lockin,
        (s.key_drivers_quantitative = '') AS missing_justification
    FROM kpi_submissions s
    JOIN departments d ON d.id = s.department_id
    WHERE s.period = COALESCE(
              NULLIF(%(period)s, ''),
              (SELECT period FROM kpi_submissions ORDER BY period_start DESC LIMIT 1)
          )
      AND (s.key_drivers_quantitative = '' OR s.kpi_lockin = FALSE)
    ORDER BY s.department_name, s.kpi_number
"""

with psycopg.connect(conn_string) as conn:
    with conn.cursor() as cur:
        cur.execute(QUERY, {"period": PERIOD})
        rows = cur.fetchall()

print(f"Found {len(rows)} outstanding KPI(s)")

# COMMAND ----------

# MAGIC %md
# MAGIC ## Build the per-region summary

# COMMAND ----------

pending = defaultdict(lambda: {"lead": "", "kpis": []})
resolved_period = PERIOD

for (department_name, lead_name, kpi_name, kpi_number, period,
     kpi_value, kpi_unit, kpi_lockin, missing_justification) in rows:
    resolved_period = period
    pending[department_name]["lead"] = lead_name
    pending[department_name]["kpis"].append({
        "kpi_name": kpi_name,
        "kpi_number": kpi_number,
        "kpi_value": kpi_value,
        "kpi_unit": kpi_unit,
        "missing_justification": missing_justification,
        "not_locked": not kpi_lockin,
    })

summary = []
for dept in sorted(pending):
    info = pending[dept]
    kpis = info["kpis"]
    summary.append({
        "department": dept,
        "lead": info["lead"],
        "count": len(kpis),
        "missing_justification": sum(1 for k in kpis if k["missing_justification"]),
        "not_locked": sum(1 for k in kpis if k["not_locked"]),
        "kpis": kpis,
    })

print(f"{len(summary)} region(s) with outstanding work for {resolved_period or '(no data)'}")

# COMMAND ----------

# MAGIC %md
# MAGIC ## Render the reminders

# COMMAND ----------

if not summary:
    print(f"Nothing outstanding for {resolved_period or 'the selected period'} — no reminders needed.")
    dbutils.notebook.exit(json.dumps({
        "status": "ok",
        "period": resolved_period,
        "pending_count": 0,
        "departments": [],
    }))

for dept in summary:
    kpi_lines = []
    for k in dept["kpis"]:
        reasons = []
        if k["missing_justification"]:
            reasons.append("no justification")
        if k["not_locked"]:
            reasons.append("not locked in")
        value = "—" if k["kpi_value"] is None else f"{k['kpi_value']} {k['kpi_unit']}".strip()
        kpi_lines.append(f"  • {k['kpi_name']}: {value} ({', '.join(reasons)})")

    print(f"""
REMINDER — {dept['department']} ({dept['lead']})
{dept['count']} KPI(s) outstanding for {resolved_period}:
  {dept['missing_justification']} missing a justification, {dept['not_locked']} not yet locked in

{chr(10).join(kpi_lines)}

Complete them at: {SUBMISSION_URL}
""")

# COMMAND ----------

# MAGIC %md
# MAGIC ## Exit with a JSON summary
# MAGIC
# MAGIC A downstream Job task can read this via `dbutils.notebook.run` and fan the
# MAGIC reminders out to email or Slack.

# COMMAND ----------

result = {
    "status": "reminders_rendered",
    "period": resolved_period,
    "pending_count": sum(d["count"] for d in summary),
    "submission_url": SUBMISSION_URL,
    "departments": summary,
}

print(json.dumps(result, indent=2, default=str))
dbutils.notebook.exit(json.dumps(result, default=str))
