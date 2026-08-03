# Databricks notebook source
# MAGIC %md
# MAGIC # Setup Lakebase Change Data Feed (CDF) — Forward ETL
# MAGIC
# MAGIC > **Note:** this feature was previously called **Lakehouse Sync**. In the
# MAGIC > current workspace UI it appears as **Lakebase Change Data Feed (CDF)**
# MAGIC > (shortened to "Lakebase CDF" below).
# MAGIC
# MAGIC Configures CDC-based continuous replication from Lakebase PostgreSQL to Delta tables
# MAGIC so new KPI submissions appear in the Genie Space automatically — no manual notebook
# MAGIC runs needed.
# MAGIC
# MAGIC **Steps:**
# MAGIC 1. Set `REPLICA IDENTITY FULL` on source tables (required for CDC)
# MAGIC 2. Create the destination Unity Catalog schema (idempotent)
# MAGIC 3. Create the Lakebase CDF configuration via the SDK (idempotent)
# MAGIC 4. Wait for the tables to reach STREAMING state
# MAGIC 5. Create clean views on top of CDC history tables for Genie
# MAGIC 6. Verification summary
# MAGIC
# MAGIC ## Configure
# MAGIC
# MAGIC Use the widgets at the top of the notebook to pick the destination Unity Catalog
# MAGIC catalog and schema. The catalog must already exist (catalog creation is a
# MAGIC metastore-admin operation); the schema is created for you in Step 2.

# COMMAND ----------

# MAGIC %pip install -U "databricks-sdk>=0.123.0" "psycopg[binary]>=3.0"
# MAGIC dbutils.library.restartPython()
# MAGIC # databricks-sdk is upgraded so the `w.postgres.*` connection-info calls
# MAGIC # below work — that service is newer than the SDK bundled in the runtime.

# COMMAND ----------

import psycopg

from databricks.sdk import WorkspaceClient

# The SDK auto-authenticates inside a notebook — no manual API token / headers.
w = WorkspaceClient()

# Create widgets — adjust their values in the toolbar at the top of the
# notebook, then run the next cell to read them.
dbutils.widgets.text("target_catalog", "main", "Target catalog")
dbutils.widgets.text("target_schema", "kpi_reporting", "Target schema")
dbutils.widgets.text("lakebase_project", "kpi-reporting", "Lakebase project")

# COMMAND ----------

# Read widget values
CATALOG = dbutils.widgets.get("target_catalog").strip()
SCHEMA = dbutils.widgets.get("target_schema").strip()
LAKEBASE_PROJECT_ID = dbutils.widgets.get("lakebase_project").strip()

# Lakebase CDF writes the CDC history tables into the same destination,
# so source-of-truth tables and history tables share catalog/schema.
SYNC_CATALOG = CATALOG
SYNC_SCHEMA = SCHEMA

TABLES = ["departments", "monthly_reporting_userbase", "kpi_submissions"]

print(f"Target:           {CATALOG}.{SCHEMA}")
print(f"Lakebase project: {LAKEBASE_PROJECT_ID}")
print(f"Tables to sync:   {TABLES}")

# COMMAND ----------

# Lakebase connection info — all via the SDK (no manual API token / REST headers).
ENDPOINT_NAME = f"projects/{LAKEBASE_PROJECT_ID}/branches/production/endpoints/primary"

pg_host = w.postgres.get_endpoint(name=ENDPOINT_NAME).status.hosts.host
# Short-lived OAuth credential used as the Postgres password.
pg_token = w.postgres.generate_database_credential(endpoint=ENDPOINT_NAME).token
username = w.current_user.me().user_name

conn_string = f"host={pg_host} dbname=databricks_postgres user={username} password={pg_token} sslmode=require"

print(f"Connected to Lakebase: {pg_host}")

# COMMAND ----------

# MAGIC %md
# MAGIC ## Step 1 — Set REPLICA IDENTITY FULL
# MAGIC
# MAGIC Lakebase CDF uses CDC (Change Data Capture) via PostgreSQL logical
# MAGIC replication. `REPLICA IDENTITY FULL` ensures UPDATE and DELETE events
# MAGIC include the full row, which is required for correct replication.

# COMMAND ----------

with psycopg.connect(conn_string) as conn:
    with conn.cursor() as cur:
        for table in TABLES:
            cur.execute(f"ALTER TABLE {table} REPLICA IDENTITY FULL")
            print(f"Set REPLICA IDENTITY FULL on: {table}")
    conn.commit()

print("\nAll tables configured for CDC.")

# COMMAND ----------

# MAGIC %md
# MAGIC ## Step 2 — Create destination schema
# MAGIC
# MAGIC Lakebase CDF needs the destination schema to exist before activation.
# MAGIC The catalog you picked in the widgets must already exist; this cell
# MAGIC creates the schema underneath it if it isn't there yet.

# COMMAND ----------

# Verify catalog exists, fail fast with a clear message if not
existing_catalogs = {row.catalog for row in spark.sql("SHOW CATALOGS").collect()}
if CATALOG not in existing_catalogs:
    raise ValueError(
        f"Catalog '{CATALOG}' does not exist in this workspace.\n"
        f"Available catalogs: {sorted(existing_catalogs)}\n"
        f"Either pick a different catalog in the 'Target catalog' widget, "
        f"or ask a metastore admin to create '{CATALOG}'."
    )

spark.sql(f"CREATE SCHEMA IF NOT EXISTS `{CATALOG}`.`{SCHEMA}`")
print(f"Schema ready: {CATALOG}.{SCHEMA}")

# COMMAND ----------

# MAGIC %md
# MAGIC ## Step 3 — Activate Lakebase CDF (SDK)
# MAGIC
# MAGIC Creates a CDF configuration via `w.postgres.create_cdf_config`, which
# MAGIC continuously replicates all tables in the Postgres `public` schema to Delta
# MAGIC tables in Unity Catalog. The configuration is immutable once created —
# MAGIC idempotent on re-runs (skips creation if the config already exists).
# MAGIC
# MAGIC > ⏳ **The first run blocks for a few minutes** while the initial table snapshot
# MAGIC > completes. Re-runs are instant (config already exists, tables already streaming).

# COMMAND ----------

from databricks.sdk.errors import NotFound
from databricks.sdk.service.postgres import CdfConfig

# The CDF config lives under the database, not just the project.
# Lakebase creates one default database called `databricks_postgres`.
_databases = list(w.postgres.list_databases(
    parent=f"projects/{LAKEBASE_PROJECT_ID}/branches/production"
))
if not _databases:
    raise ValueError(
        f"No databases found under projects/{LAKEBASE_PROJECT_ID}/branches/production. "
        "Did notebook 01 finish creating the project?"
    )
_db_path = _databases[0].name   # "projects/<id>/branches/production/databases/<uid>"
_cdf_config_id = "public"       # matches the Postgres schema name
_config_path = f"{_db_path}/cdf-configs/{_cdf_config_id}"

print(f"Database path: {_db_path}")
print(f"CDF config path: {_config_path}")

# --- Create CDF config (idempotent: get → create) ---
try:
    existing = w.postgres.get_cdf_config(name=_config_path)
    print(f"CDF config already exists ({existing.name}) — skipping creation.")
except NotFound:
    print(f"Creating CDF config: postgres public → {CATALOG}.{SCHEMA} ...")
    op = w.postgres.create_cdf_config(
        parent=_db_path,
        cdf_config=CdfConfig(
            catalog=CATALOG,
            postgres_schema="public",
            schema=SCHEMA,
        ),
        cdf_config_id=_cdf_config_id,
    )
    # .wait() blocks until the long-running operation finishes; raises on failure.
    result = op.wait()
    print(f"CDF config created: {result.name}")

# COMMAND ----------

# MAGIC %md
# MAGIC ## Step 4 — Wait for tables to start streaming
# MAGIC
# MAGIC Each table transitions `CDF_STATE_SNAPSHOTTING` (initial data copy) →
# MAGIC `CDF_STATE_STREAMING` (live CDC). The initial snapshot typically takes 1–3 minutes.

# COMMAND ----------

import time

from databricks.sdk.service.postgres import CdfState

STREAMING = CdfState.CDF_STATE_STREAMING
SNAPSHOTTING = CdfState.CDF_STATE_SNAPSHOTTING
EXPECTED_TABLES = set(TABLES)

sync_active = False
statuses = []
streaming = set()
snapshotting = set()
status_lines = []
print(f"Waiting for all {len(EXPECTED_TABLES)} tables to reach STREAMING...")

for _attempt in range(60):
    statuses = list(w.postgres.list_cdf_statuses(parent=_config_path))
    by_table = {s.postgres_table: s.state for s in statuses}

    streaming = {t for t, st in by_table.items() if st == STREAMING}
    snapshotting = {t for t, st in by_table.items() if st == SNAPSHOTTING}

    status_lines = []
    for t in sorted(EXPECTED_TABLES):
        st = by_table.get(t)
        icon = "✅" if st == STREAMING else ("⏳" if st == SNAPSHOTTING else "❓")
        status_lines.append(f"  {icon} {t}: {st.value if st else 'NOT_FOUND'}")

    summary = "  |  ".join(
        f"{t}={by_table.get(t, '?')}" for t in sorted(EXPECTED_TABLES)
    )
    print(f"[{_attempt+1:02d}] {summary}")

    if EXPECTED_TABLES <= streaming:
        sync_active = True
        print("\nAll tables streaming ✅")
        break

    time.sleep(10)
else:
    print(f"\nTimeout. Streaming: {streaming}. Snapshotting: {snapshotting}.")
    print("Continuing — views will be created over whatever data has landed so far.")
    sync_active = bool(statuses)

for line in status_lines:
    print(line)

# COMMAND ----------

# MAGIC %md
# MAGIC ## Step 5 — Create clean views for Genie
# MAGIC
# MAGIC Lakebase CDF creates `lb_<table>_history` tables with CDC columns
# MAGIC (`_change_type`, `_timestamp`, `_lsn`, `_xid`). These views filter to the
# MAGIC latest row state so the Genie Space can query them without reconfiguration.

# COMMAND ----------

if not sync_active:
    print("Skipping view creation — Lakebase CDF is not active yet (no tables streaming).")
    print("Check Steps 3 and 4 above for errors, then re-run this notebook.")
else:
    # Lakebase CDF adds these CDC metadata columns to every history table.
    # _pg_change_type values: 'insert', 'update_postimage', 'delete'
    # _sort_by is monotonically increasing — use it for ordering.
    CDC_COLUMNS = {"_pg_change_type", "_pg_lsn", "_pg_xid", "_sort_by", "_timestamp"}

    # Primary key for each source table — used to PARTITION BY when picking
    # the latest row per logical record. Tables that don't have a single-
    # column PK go in here too.
    PK_COLUMN = {
        "departments": "id",
        "monthly_reporting_userbase": "employee_business_email",
        "kpi_submissions": "id",
    }

    for table in TABLES:
        history_fqn = f"{SYNC_CATALOG}.{SYNC_SCHEMA}.lb_{table}_history"
        history_table = f"`{SYNC_CATALOG}`.`{SYNC_SCHEMA}`.`lb_{table}_history`"
        view_name = f"`{CATALOG}`.`{SCHEMA}`.`{table}`"
        pk = PK_COLUMN[table]

        # Drop any existing object (table or view) so we can create the view
        for stmt in (f"DROP TABLE IF EXISTS {view_name}", f"DROP VIEW IF EXISTS {view_name}"):
            try:
                spark.sql(stmt)
            except Exception:
                pass

        # Get business columns (everything that isn't CDC metadata)
        all_columns = [
            col.name for col in spark.table(history_fqn).schema
            if col.name not in CDC_COLUMNS
        ]
        select_cols = ", ".join(f"`{c}`" for c in all_columns)

        spark.sql(f"""
            CREATE OR REPLACE VIEW {view_name} AS
            SELECT {select_cols}
            FROM (
                SELECT *,
                    ROW_NUMBER() OVER (PARTITION BY `{pk}` ORDER BY `_sort_by` DESC) AS _rn
                FROM {history_table}
                WHERE `_pg_change_type` IN ('insert', 'update_postimage')
            )
            WHERE _rn = 1
        """)
        print(f"Created view: {CATALOG}.{SCHEMA}.{table}  (PK: {pk})")

# COMMAND ----------

# MAGIC %md
# MAGIC ## Step 6 — Governed KPI metric view (Unity Catalog)
# MAGIC
# MAGIC Define the KPIs once as a **Unity Catalog metric view** so Genie, AI/BI
# MAGIC dashboards, and the app all share one governed definition. Ratios like
# MAGIC *Lock Rate* and *Avg Achievement* re-aggregate correctly at any grouping —
# MAGIC which a plain view can't do. A tiny `kpi_targets` reference table supplies
# MAGIC per-KPI targets (mirroring notebook 01's KPI definitions) so *Achievement*
# MAGIC is expressible; `higher_is_better` flips the ratio for "lower is better"
# MAGIC KPIs (DSO, OPEX Ratio) so ~100% always means "on target".
# MAGIC
# MAGIC > Requires **DBR 17.2+** (metric-view YAML v1.1) — serverless is current. If
# MAGIC > your compute can't run `CREATE VIEW … WITH METRICS` via Spark, run the same
# MAGIC > statement on a SQL warehouse.

# COMMAND ----------

if not sync_active:
    print("Skipping metric view — Lakebase CDF is not active yet (the kpi_submissions view must exist first).")
    print("Re-run the notebook once Steps 3–5 complete.")
else:
    from pyspark.sql import Row

    # Per-KPI targets — governed reference data for the analytical layer.
    # (number, name, target_value, unit, higher_is_better) — mirrors notebook 01 KPI_DEFINITIONS.
    # NOTE: these must match notebook 01's KPI_DEFINITIONS exactly (same kpi_number).
    KPI_TARGETS = [
        (1, "Revenue Growth",   8.5,       "%",    True),
        (2, "Operating Margin", 14.0,      "%",    True),
        (3, "DSO",              52.0,      "days", False),
        (4, "OPEX Ratio",       22.0,      "%",    False),
        (5, "Free Cash Flow",   4200000.0, "USD",  True),
    ]
    spark.createDataFrame(
        [Row(kpi_number=n, kpi_name=nm, target_value=tv, kpi_unit=u, higher_is_better=hb)
         for (n, nm, tv, u, hb) in KPI_TARGETS]
    ).write.mode("overwrite").option("overwriteSchema", "true").saveAsTable(f"{CATALOG}.{SCHEMA}.kpi_targets")
    print(f"Created reference table: {CATALOG}.{SCHEMA}.kpi_targets ({len(KPI_TARGETS)} rows)")

    # Build the metric-view YAML line-by-line. YAML is whitespace-sensitive, so we
    # keep each line's indentation explicit rather than relying on code indentation.
    yaml_lines = [
        "version: 1.1",
        'comment: "Governed financial KPI metrics — shared by Genie, dashboards, and the app"',
        f"source: {CATALOG}.{SCHEMA}.kpi_submissions",
        "joins:",
        "  - name: dept",
        f"    source: {CATALOG}.{SCHEMA}.departments",
        "    on: source.department_id = dept.id",
        "  - name: tgt",
        f"    source: {CATALOG}.{SCHEMA}.kpi_targets",
        "    on: source.kpi_number = tgt.kpi_number",
        "dimensions:",
        "  - name: Region",
        "    expr: department_name",
        "  - name: Regional Lead",
        "    expr: dept.lead_name",
        "  - name: KPI",
        "    expr: kpi_name",
        "  - name: KPI Category",
        "    expr: kpi_category",
        "  - name: Reporting Month",
        "    expr: period_start",
        "  - name: Period",
        "    expr: period",
        "  - name: Status",
        "    expr: CASE WHEN kpi_lockin THEN 'Locked' ELSE 'Pending' END",
        "measures:",
        "  - name: Submissions",
        "    expr: COUNT(1)",
        "  - name: Locked Submissions",
        "    expr: COUNT_IF(kpi_lockin)",
        "  - name: Lock Rate",
        "    expr: COUNT_IF(kpi_lockin) / COUNT(1)",
        "  - name: Reviewed Rate",
        "    expr: COUNT_IF(reviewed_by_gm <> '') / COUNT(1)",
        "  - name: Regions Reporting",
        "    expr: COUNT(DISTINCT department_id)",
        "  - name: Avg KPI Value",
        "    expr: AVG(kpi_value)",
        "  - name: Avg Achievement",
        "    expr: AVG(CASE WHEN tgt.higher_is_better THEN kpi_value / NULLIF(tgt.target_value, 0) ELSE tgt.target_value / NULLIF(kpi_value, 0) END)",
    ]
    yaml_body = "\n".join(yaml_lines)
    spark.sql(
        f"CREATE OR REPLACE VIEW `{CATALOG}`.`{SCHEMA}`.kpi_metrics "
        f"WITH METRICS LANGUAGE YAML AS $$\n{yaml_body}\n$$"
    )
    print(f"Created metric view: {CATALOG}.{SCHEMA}.kpi_metrics")
    print("Query measures with MEASURE(), e.g.:")
    print(f"  SELECT `Region`, MEASURE(`Avg Achievement`), MEASURE(`Lock Rate`)")
    print(f"  FROM {CATALOG}.{SCHEMA}.kpi_metrics GROUP BY ALL ORDER BY ALL")

# COMMAND ----------

# MAGIC %md
# MAGIC ## Step 7 — Verification summary

# COMMAND ----------

if not sync_active:
    print("Skipping verification — Lakebase CDF is not active yet.")
    print("\nDone so far: Step 1 (REPLICA IDENTITY), Step 2 (destination schema), Step 3 (CDF config created).")
    print("Re-run the notebook — Step 4 will wait for tables to reach STREAMING state.")
else:
    print(f"{'View':<60} {'Rows'}")
    print("-" * 70)
    for table in TABLES:
        view_name = f"{CATALOG}.{SCHEMA}.{table}"
        count = spark.table(view_name).count()
        print(f"{view_name:<60} {count}")

    print(f"\nLakebase CDF setup complete in {CATALOG}.{SCHEMA}")
    print("Now run notebook 03 — its Genie Space points at the governed metric view + tables:")
    for table in ("kpi_metrics", "departments", "kpi_submissions"):
        print(f"  - {CATALOG}.{SCHEMA}.{table}")
