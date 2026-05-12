# Databricks notebook source
# MAGIC %md
# MAGIC # Setup Lakehouse Sync (Forward ETL)
# MAGIC
# MAGIC Configures CDC-based continuous replication from Lakebase PostgreSQL to Delta tables
# MAGIC so new KPI submissions appear in the Genie Space automatically — no manual notebook
# MAGIC runs needed.
# MAGIC
# MAGIC **Steps:**
# MAGIC 1. Set `REPLICA IDENTITY FULL` on source tables (required for CDC)
# MAGIC 2. Create the destination Unity Catalog schema (idempotent)
# MAGIC 3. One-time UI activation of Lakehouse Sync — instructions render with your
# MAGIC    widget values
# MAGIC 4. Verify sync status
# MAGIC 5. Create clean views on top of CDC history tables for Genie
# MAGIC 6. Verification summary
# MAGIC
# MAGIC ## Configure
# MAGIC
# MAGIC Use the widgets at the top of the notebook to pick the destination Unity Catalog
# MAGIC catalog and schema. The catalog must already exist (catalog creation is a
# MAGIC metastore-admin operation); the schema is created for you in Step 2.

# COMMAND ----------

# MAGIC %pip install -U "psycopg[binary]>=3.0"
# MAGIC dbutils.library.restartPython()

# COMMAND ----------

import requests
import psycopg

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

# Lakehouse Sync writes the CDC history tables into the same destination,
# so source-of-truth tables and history tables share catalog/schema.
SYNC_CATALOG = CATALOG
SYNC_SCHEMA = SCHEMA

TABLES = ["departments", "monthly_reporting_userbase", "kpi_submissions"]

print(f"Target:           {CATALOG}.{SCHEMA}")
print(f"Lakebase project: {LAKEBASE_PROJECT_ID}")
print(f"Tables to sync:   {TABLES}")

# COMMAND ----------

# Workspace context
ctx = dbutils.notebook.entry_point.getDbutils().notebook().getContext()
host = ctx.apiUrl().get()
token = ctx.apiToken().get()
headers = {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}

# COMMAND ----------

# Lakebase connection
endpoint_path = f"projects/{LAKEBASE_PROJECT_ID}/branches/production/endpoints/primary"

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

conn_string = f"host={pg_host} dbname=databricks_postgres user={username} password={pg_token} sslmode=require"

print(f"Connected to Lakebase: {pg_host}")

# COMMAND ----------

# MAGIC %md
# MAGIC ## Step 1 — Set REPLICA IDENTITY FULL
# MAGIC
# MAGIC Lakehouse Sync uses CDC (Change Data Capture) via PostgreSQL logical
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
# MAGIC Lakehouse Sync needs the destination schema to exist before activation.
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
# MAGIC ## Step 3 — Activate Lakehouse Sync (one-time UI step)
# MAGIC
# MAGIC Lakehouse Sync does not yet have a REST API — activation must be done
# MAGIC through the workspace UI. The cell below renders the exact values to
# MAGIC plug into the form based on your widget settings.

# COMMAND ----------

displayHTML(f"""
<div style="padding: 16px 20px; background: #fff8e1; border-left: 4px solid #f5a623; border-radius: 6px; font-family: -apple-system, system-ui, sans-serif;">
  <h3 style="margin: 0 0 12px 0;">Activate Lakehouse Sync (UI)</h3>
  <ol style="line-height: 1.7;">
    <li>Open <strong>Lakebase</strong> in the workspace sidebar</li>
    <li>Select project <strong>{LAKEBASE_PROJECT_ID}</strong> → branch <strong>production</strong></li>
    <li>Open the <strong>Branch overview</strong> → <strong>Lakehouse sync</strong> tab</li>
    <li>Click <strong>Start sync</strong></li>
    <li>Configure with these values:
      <table style="margin-top: 8px; border-collapse: collapse;">
        <tr><td style="padding: 4px 12px 4px 0;">Source database</td><td><code>databricks_postgres</code></td></tr>
        <tr><td style="padding: 4px 12px 4px 0;">Source schema</td><td><code>public</code></td></tr>
        <tr><td style="padding: 4px 12px 4px 0;">Destination catalog</td><td><code>{CATALOG}</code></td></tr>
        <tr><td style="padding: 4px 12px 4px 0;">Destination schema</td><td><code>{SCHEMA}</code></td></tr>
      </table>
    </li>
    <li>Confirm and start the sync</li>
  </ol>
  <p style="margin: 12px 0 0 0; font-size: 13px; color: #555;">
    Once activated, Lakehouse Sync will continuously replicate changes from
    PostgreSQL to Delta tables named <code>lb_&lt;table&gt;_history</code>
    in <code>{CATALOG}.{SCHEMA}</code>. Then re-run this notebook from Step 4
    to create the clean views Genie reads.
  </p>
</div>
""")

# COMMAND ----------

# MAGIC %md
# MAGIC ## Step 4 — Verify sync status
# MAGIC
# MAGIC Query the `wal2delta.tables` system table to confirm all tables are syncing.

# COMMAND ----------

sync_active = False
try:
    with psycopg.connect(conn_string) as conn:
        with conn.cursor() as cur:
            cur.execute("SELECT * FROM wal2delta.tables LIMIT 0")
            col_names = [desc[0] for desc in cur.description]
            print(f"wal2delta.tables columns: {col_names}")

            cur.execute("SELECT * FROM wal2delta.tables ORDER BY 1")
            rows = cur.fetchall()

    if not rows:
        print("No sync entries found. Has Lakehouse Sync been activated? (See Step 3)")
    else:
        sync_active = True
        for row in rows:
            print(dict(zip(col_names, row)))
except Exception as e:
    if "wal2delta" in str(e).lower():
        print("Lakehouse Sync has not been activated yet — wal2delta schema does not exist.")
        print("Complete the one-time UI activation in Step 3, then re-run this notebook.")
    else:
        raise

# COMMAND ----------

# MAGIC %md
# MAGIC ## Step 5 — Create clean views for Genie
# MAGIC
# MAGIC Lakehouse Sync creates `lb_<table>_history` tables with CDC columns
# MAGIC (`_change_type`, `_timestamp`, `_lsn`, `_xid`). These views filter to the
# MAGIC latest row state so the Genie Space can query them without reconfiguration.

# COMMAND ----------

if not sync_active:
    print("Skipping view creation — Lakehouse Sync is not active yet.")
    print("Complete the one-time UI activation in Step 3, then re-run this notebook.")
else:
    # Lakehouse Sync adds these CDC metadata columns to every history table.
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
# MAGIC ## Step 6 — Verification summary

# COMMAND ----------

if not sync_active:
    print("Skipping verification — Lakehouse Sync is not active yet.")
    print("\nDone so far: Step 1 (REPLICA IDENTITY) and Step 2 (destination schema).")
    print("Next:")
    print("  1. Complete the one-time UI activation (Step 3 above)")
    print("  2. Re-run this notebook to create views and verify")
else:
    print(f"{'View':<60} {'Rows'}")
    print("-" * 70)
    for table in TABLES:
        view_name = f"{CATALOG}.{SCHEMA}.{table}"
        count = spark.table(view_name).count()
        print(f"{view_name:<60} {count}")

    print(f"\nLakehouse Sync setup complete in {CATALOG}.{SCHEMA}")
    print("Now create the Genie Space and select these tables:")
    for table in ("departments", "kpi_submissions"):
        print(f"  - {CATALOG}.{SCHEMA}.{table}")
