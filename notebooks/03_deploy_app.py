# Databricks notebook source
# MAGIC %md
# MAGIC # Deploy Guide — Genie Space + App
# MAGIC
# MAGIC Final step of the deploy. Each part runs through the SDK/API — creating the
# MAGIC Genie Space, minting/storing secrets, creating the app, and attaching resources.
# MAGIC
# MAGIC **Prerequisites — finish these first:**
# MAGIC - Notebook **`01_setup_lakebase.py`** (Lakebase project + tables seeded)
# MAGIC - Notebook **`02_setup_forward_etl.py`** (Lakebase CDF — Change Data Feed, formerly "Lakehouse Sync" — running, Delta views in place)
# MAGIC
# MAGIC | Step | What happens | How |
# MAGIC |---|---|---|
# MAGIC | 1. Create Genie Space | Over the Delta views, with KPI instructions | `w.genie.create_space` (SDK cell below) |
# MAGIC | 2. Confluence API token | Mint a token + find URL parts | Atlassian UI |
# MAGIC | 2d. Store the token | As a Databricks secret | SDK cell below |
# MAGIC | 3. Create the App + resources | Lakebase, Genie, secret | SDK cell below |
# MAGIC | 3b. Grant App SP access | UC + Lakebase grants for the App's service principal | SDK cell below |
# MAGIC | 4. Build & deploy the App | Build wheel + app.yml + apps.deploy | SDK cell below |
# MAGIC | 5. Smoke test | Verify the app works | Browser |

# COMMAND ----------

# MAGIC %pip install -U "databricks-sdk>=0.74.0" "psycopg[binary]>=3.0"
# MAGIC dbutils.library.restartPython()

# COMMAND ----------

# MAGIC %md
# MAGIC ## Configure
# MAGIC
# MAGIC The cell below creates widgets for everything the SDK calls need. Adjust
# MAGIC values in the toolbar at the top of the notebook, then run the next
# MAGIC cell to read them.

# COMMAND ----------

# Create widgets — adjust their values via the toolbar at the top of the notebook
dbutils.widgets.text("app_name", "kpi-reporting", "App name")
dbutils.widgets.text("lakebase_project", "kpi-reporting", "Lakebase project")
dbutils.widgets.text("genie_space_id", "", "Genie Space ID (blank = auto-create in Step 1)")
dbutils.widgets.text("genie_warehouse_id", "", "SQL warehouse ID for the Genie Space (Step 1)")
# Catalog and schema where Lakebase CDF wrote the Delta views — must match
# whatever you picked in notebook 02's widgets.
dbutils.widgets.text("target_catalog", "main", "Target catalog (from notebook 02)")
dbutils.widgets.text("target_schema", "kpi_reporting", "Target schema (from notebook 02)")

# Confluence is optional — the publish-to-wiki feature is disabled if you say no.
# When set to "no" you can leave all the confluence_* widgets blank.
dbutils.widgets.dropdown("enable_confluence", "no", ["no", "yes"], "Enable Confluence publishing")
dbutils.widgets.text("secret_scope", "kpi-reporting", "Secret scope name")
dbutils.widgets.text("secret_key", "confluence_api_token", "Secret key")
dbutils.widgets.text("confluence_token", "", "Confluence API token (clear after Step 2d)")
dbutils.widgets.text("confluence_base_url", "https://your-org.atlassian.net/wiki", "Confluence base URL")
dbutils.widgets.text("confluence_user_email", "", "Confluence user email")
dbutils.widgets.text("confluence_space_key", "", "Confluence space key")
dbutils.widgets.text("confluence_parent_page_id", "", "Confluence parent page ID")

# COMMAND ----------

# Read widgets into Python constants
APP_NAME = dbutils.widgets.get("app_name").strip()
LAKEBASE_PROJECT = dbutils.widgets.get("lakebase_project").strip()
GENIE_SPACE_ID = dbutils.widgets.get("genie_space_id").strip()
GENIE_WAREHOUSE_ID = dbutils.widgets.get("genie_warehouse_id").strip()
TARGET_CATALOG = dbutils.widgets.get("target_catalog").strip()
TARGET_SCHEMA = dbutils.widgets.get("target_schema").strip()
ENABLE_CONFLUENCE = dbutils.widgets.get("enable_confluence") == "yes"
SECRET_SCOPE = dbutils.widgets.get("secret_scope").strip()
SECRET_KEY = dbutils.widgets.get("secret_key").strip()
CONFLUENCE_TOKEN = dbutils.widgets.get("confluence_token")
CONFLUENCE_BASE_URL = dbutils.widgets.get("confluence_base_url").strip()
CONFLUENCE_USER_EMAIL = dbutils.widgets.get("confluence_user_email").strip()
CONFLUENCE_SPACE_KEY = dbutils.widgets.get("confluence_space_key").strip()
CONFLUENCE_PARENT_PAGE_ID = dbutils.widgets.get("confluence_parent_page_id").strip()

print(f"App name:         {APP_NAME}")
print(f"Lakebase project: {LAKEBASE_PROJECT}")
print(f"Delta target:     {TARGET_CATALOG}.{TARGET_SCHEMA}")
print(f"Genie Space ID:   {GENIE_SPACE_ID or '(blank — Step 1 will create the Space)'}")
print(f"Confluence:       {'enabled' if ENABLE_CONFLUENCE else 'disabled (publish-to-wiki feature off)'}")
if ENABLE_CONFLUENCE:
    print(f"Secret:           {SECRET_SCOPE}/{SECRET_KEY}")
    print(f"Token in widget:  {'<provided>' if CONFLUENCE_TOKEN else '(empty — fill before Step 2d)'}")
    print(f"Confluence URL:   {CONFLUENCE_BASE_URL}")
    print(f"Confluence email: {CONFLUENCE_USER_EMAIL or '(not set yet)'}")
    print(f"Confluence space: {CONFLUENCE_SPACE_KEY or '(not set yet)'}")
    print(f"Parent page ID:   {CONFLUENCE_PARENT_PAGE_ID or '(not set yet)'}")

# COMMAND ----------

# MAGIC %md
# MAGIC ## Step 1 — Create the Genie Space (automated via API)
# MAGIC
# MAGIC The Genie Space gives the CFO persona natural-language Q&A over the KPI data.
# MAGIC Genie now has a public API (`w.genie.create_space`), so the cell below creates
# MAGIC the Space for you — no manual UI clicks.
# MAGIC
# MAGIC **Before running:**
# MAGIC - Notebook 02 must have finished — the Delta views must exist, since
# MAGIC   `create_space` references them.
# MAGIC - Set the **`genie_warehouse_id`** widget to a SQL warehouse ID (Genie runs its
# MAGIC   generated SQL on a warehouse; find one under **SQL Warehouses** in the UI).
# MAGIC - Leave **`genie_space_id`** blank to create a new Space; if it's already set,
# MAGIC   creation is skipped and the existing Space is reused.
# MAGIC
# MAGIC A manual UI fallback (if you'd rather click through it, or the API isn't enabled
# MAGIC in your workspace) is in the appendix cell just below.

# COMMAND ----------

import json
import uuid
from databricks.sdk import WorkspaceClient

w = WorkspaceClient()

# Tables the Space queries (created by notebook 02). monthly_reporting_userbase
# is intentionally left out — it's only used by the app for SSO mapping and isn't
# useful for AI Q&A.
GENIE_TABLES = [
    f"{TARGET_CATALOG}.{TARGET_SCHEMA}.kpi_metrics",       # governed metric view (notebook 02) — measures like Avg Achievement, Lock Rate
    f"{TARGET_CATALOG}.{TARGET_SCHEMA}.departments",
    f"{TARGET_CATALOG}.{TARGET_SCHEMA}.kpi_submissions",   # row-level detail for drill-down questions
]

# System instructions that help Genie analyse the KPI data accurately. Edit freely;
# this becomes one instruction block in the Space's Settings → Instructions.
GENIE_INSTRUCTIONS = [
    "You are a financial analyst assistant specializing in multi-region KPI ",
    "performance analysis. Help executives understand KPI trends, regional ",
    "performance, and the key drivers behind results.\n\n",
    "Data model:\n",
    "- Each row in `kpi_submissions` is one KPI (e.g. Revenue Growth, Operating ",
    "Margin) for one region and one reporting period.\n",
    "- `kpi_value` is the actual reported number; its unit is in `kpi_unit`.\n",
    "- `kpi_lockin = TRUE` means the regional lead locked and formally submitted the data.\n",
    "- `key_drivers_quantitative` / `key_drivers_qualitative` explain WHY the KPI landed where it did.\n",
    "- `departments` joins to `kpi_submissions` on `department_id` for region names.\n",
    "- `kpi_metrics` is a governed Unity Catalog metric view — prefer it for aggregate ",
    "questions. Query its measures (Submissions, Lock Rate, Reviewed Rate, Regions ",
    "Reporting, Avg KPI Value, Avg Achievement) grouped by its dimensions (Region, KPI, ",
    "KPI Category, Reporting Month, Status). `Avg Achievement` already accounts for KPI ",
    "direction (for DSO and OPEX Ratio, lower actuals are better), so ~1.0 means on target.\n\n",
    "Analysis guidance:\n",
    "- Focus on trends across months, regional comparisons, and achievement rates.\n",
    "- Highlight under- and over-performers, and use the key_drivers columns to ",
    "explain outliers rather than just reporting numbers.",
]

if GENIE_SPACE_ID:
    print(f"genie_space_id already set ({GENIE_SPACE_ID}) — skipping creation, reusing it.")
else:
    if not GENIE_WAREHOUSE_ID:
        raise ValueError(
            "Set the `genie_warehouse_id` widget to a SQL warehouse ID, then re-run. "
            "(Genie runs its generated SQL on a warehouse.)"
        )
    # serialized_space is the Space definition as a JSON string (schema v2:
    # data_sources + instructions). create_space takes this plus a warehouse.
    serialized_space = json.dumps({
        "version": 2,
        # create_space requires data_sources.tables sorted by identifier.
        "data_sources": {"tables": [{"identifier": t} for t in sorted(GENIE_TABLES)]},
        "instructions": {"text_instructions": [{"id": uuid.uuid4().hex, "content": GENIE_INSTRUCTIONS}]},
    })
    space = w.genie.create_space(
        warehouse_id=GENIE_WAREHOUSE_ID,
        serialized_space=serialized_space,
        title="Financial KPI Reporting",
        description="Natural-language Q&A over multi-region financial KPI submissions.",
    )
    GENIE_SPACE_ID = space.space_id
    print(f"Created Genie Space: {GENIE_SPACE_ID}")
    print(f"Open it: {w.config.host}/genie/rooms/{GENIE_SPACE_ID}")
    print("Tip: paste this ID into the `genie_space_id` widget so future re-runs skip creation.")

# COMMAND ----------

# MAGIC %md
# MAGIC ### Step 1 (manual fallback) — create the Genie Space in the UI
# MAGIC
# MAGIC Only needed if you skipped the automated cell above. Otherwise continue to Step 2.
# MAGIC
# MAGIC 1. In the workspace sidebar open **Genie** → **New**
# MAGIC 2. Name it `Financial KPI Reporting`
# MAGIC 3. **Add tables** from the catalog/schema you chose in notebook 02:
# MAGIC    - `<catalog>.<schema>.departments`
# MAGIC    - `<catalog>.<schema>.kpi_submissions`
# MAGIC    (Leave `monthly_reporting_userbase` out — SSO mapping only, not useful for Q&A.)
# MAGIC 4. Open **Settings → Instructions** and paste the guidance from the
# MAGIC    `GENIE_INSTRUCTIONS` list in the cell above.
# MAGIC 5. **Copy the Space ID** (the path segment after `/genie/rooms/` in the URL)
# MAGIC    into the `genie_space_id` widget, then re-run the "Read widgets" cell.

# COMMAND ----------

# MAGIC %md
# MAGIC ## Step 2 — Confluence (optional)
# MAGIC
# MAGIC The app's "publish to Confluence" feature is disabled by default. If
# MAGIC you want to skip it, set the `enable_confluence` widget to **no**
# MAGIC (the default), leave the `confluence_*` widgets blank, and jump to
# MAGIC **Step 3** — the secret cell will be a no-op and Step 4 will deploy
# MAGIC the app without the Confluence resource or env vars.
# MAGIC
# MAGIC The rest of this step only matters if `enable_confluence = yes`.

# COMMAND ----------

# MAGIC %md
# MAGIC ### Step 2a–c — Confluence API token (manual)
# MAGIC
# MAGIC ### 2a. Mint a token
# MAGIC
# MAGIC 1. [https://id.atlassian.com/manage-profile/security/api-tokens](https://id.atlassian.com/manage-profile/security/api-tokens)
# MAGIC 2. **Create API token** → label it `kpi-reporting-app`
# MAGIC 3. Copy the token (you only see it once)
# MAGIC
# MAGIC ### 2b. Find your Confluence URL parts (paste them into the widgets above)
# MAGIC
# MAGIC | Widget | How to find the value | Example |
# MAGIC |---|---|---|
# MAGIC | `confluence_base_url` | Host root with `/wiki` suffix | `https://your-org.atlassian.net/wiki` |
# MAGIC | `confluence_user_email` | The email you log into Atlassian with | `you@your-org.com` |
# MAGIC | `confluence_space_key` | Path segment after `/spaces/`. Personal spaces look like `~712020abc...` | `KPI` |
# MAGIC | `confluence_parent_page_id` | Numeric path segment after `/pages/` | `123456789` |
# MAGIC
# MAGIC Paste these into the widgets at the top of the notebook, then re-run
# MAGIC the "Read widgets" cell. They'll be passed straight into the App
# MAGIC deployment in Step 4 — no need to edit `app.yml`.
# MAGIC
# MAGIC ### 2c. Test the token (optional)
# MAGIC
# MAGIC From your laptop:
# MAGIC
# MAGIC ```bash
# MAGIC curl -s -u "you@your-org.com:YOUR_TOKEN" \
# MAGIC   "https://your-org.atlassian.net/wiki/rest/api/space?spaceKey=KPI" | jq .
# MAGIC ```
# MAGIC
# MAGIC 401 = wrong token/email; 404 = wrong space key.

# COMMAND ----------

# MAGIC %md
# MAGIC ## Step 2d — Store the token as a Databricks secret (SDK)
# MAGIC
# MAGIC Paste the token into the `confluence_token` widget at the top, re-run
# MAGIC the "Read widgets" cell, then run the cell below. **Clear the widget
# MAGIC value afterwards** so it isn't sitting in the notebook state.

# COMMAND ----------

from databricks.sdk import WorkspaceClient
from databricks.sdk.errors.platform import ResourceAlreadyExists

w = WorkspaceClient()

if not ENABLE_CONFLUENCE:
    print("Confluence is disabled — skipping secret creation. (Flip enable_confluence=yes to set up.)")
else:
    if not CONFLUENCE_TOKEN:
        raise ValueError("Set the `confluence_token` widget before running this cell.")

    # Create the secret scope (idempotent)
    try:
        w.secrets.create_scope(scope=SECRET_SCOPE)
        print(f"Created secret scope: {SECRET_SCOPE}")
    except ResourceAlreadyExists:
        print(f"Secret scope already exists: {SECRET_SCOPE}")

    # Store the token
    w.secrets.put_secret(scope=SECRET_SCOPE, key=SECRET_KEY, string_value=CONFLUENCE_TOKEN)
    print(f"Stored secret: {SECRET_SCOPE}/{SECRET_KEY}")

    # Clear the widget so the token isn't sitting in notebook state
    dbutils.widgets.set("confluence_token", "")
    print("Cleared the `confluence_token` widget.")

# COMMAND ----------

# MAGIC %md
# MAGIC ## Step 3 — Create the App and attach resources (SDK)
# MAGIC
# MAGIC Resources are bound to the App by **name** — these names must match the
# MAGIC `valueFrom:` references in `app.yml`. Today the references are:
# MAGIC
# MAGIC | Resource name | What it provides | Why |
# MAGIC |---|---|---|
# MAGIC | `lakebase_project` | Auto-injects `PGHOST`, `PGUSER`, `ENDPOINT_NAME` | App connects to Lakebase |
# MAGIC | `genie_space` | `GENIE_SPACE_ID` env var | App calls Genie |
# MAGIC | `confluence_api_token` | `KPI_REPORTING_CONFLUENCE_API_TOKEN` env var | App publishes to Confluence |
# MAGIC
# MAGIC The cell below creates the App if it doesn't exist, or updates it if it does.
# MAGIC Either way it's idempotent — safe to re-run.

# COMMAND ----------

from databricks.sdk.service.apps import (
    App,
    AppResource,
    AppResourcePostgres,
    AppResourcePostgresPostgresPermission,
    AppResourceGenieSpace,
    AppResourceGenieSpaceGenieSpacePermission,
    AppResourceSecret,
    AppResourceSecretSecretPermission,
)
from databricks.sdk.errors.platform import NotFound

if not GENIE_SPACE_ID:
    raise ValueError("Set the `genie_space_id` widget (Step 1 → copy from Genie URL) before running this cell.")

# Discover the Lakebase database under our project — the App SDK wants full
# resource paths (`projects/<id>/branches/<b>/databases/<uid>`), not names.
branch_path = f"projects/{LAKEBASE_PROJECT}/branches/production"
databases = list(w.postgres.list_databases(parent=branch_path))
if not databases:
    raise ValueError(
        f"No Lakebase databases found under {branch_path}. "
        "Did notebook 01 finish creating the project?"
    )
db_path = databases[0].name
print(f"Lakebase database path: {db_path}")

resources = [
    AppResource(
        name="lakebase_project",
        postgres=AppResourcePostgres(
            branch=branch_path,
            database=db_path,
            permission=AppResourcePostgresPostgresPermission.CAN_CONNECT_AND_CREATE,
        ),
    ),
    AppResource(
        name="genie_space",
        genie_space=AppResourceGenieSpace(
            name="Financial KPI Reporting",
            space_id=GENIE_SPACE_ID,
            permission=AppResourceGenieSpaceGenieSpacePermission.CAN_RUN,
        ),
    ),
]
if ENABLE_CONFLUENCE:
    resources.append(
        AppResource(
            name="confluence_api_token",
            secret=AppResourceSecret(
                scope=SECRET_SCOPE,
                key=SECRET_KEY,
                permission=AppResourceSecretSecretPermission.READ,
            ),
        )
    )

app_spec = App(
    name=APP_NAME,
    description="Financial KPI Reporting reference app",
    resources=resources,
)

try:
    existing = w.apps.get(name=APP_NAME)
    print(f"App {APP_NAME} already exists — updating resources...")
    w.apps.update(name=APP_NAME, app=app_spec)
    print(f"Updated: {APP_NAME}")
except NotFound:
    print(f"Creating app {APP_NAME}...")
    w.apps.create_and_wait(app=app_spec)
    print(f"Created: {APP_NAME}")

print("\nResources attached:")
for r in resources:
    kind = next(k for k in ("postgres", "genie_space", "secret") if getattr(r, k) is not None)
    print(f"  - {r.name} ({kind})")

# COMMAND ----------

# MAGIC %md
# MAGIC ## Step 3b — Grant the App's service principal access
# MAGIC
# MAGIC The App runs as its own service principal. Tables created in notebook 01
# MAGIC are owned by you, and the synced Delta views are owned by whoever ran
# MAGIC notebook 02 — neither grants any access to the SP by default. Without
# MAGIC explicit grants:
# MAGIC
# MAGIC - **Submission edits silently fail** (Lakebase rejects INSERT/UPDATE)
# MAGIC - **Genie chat returns FAILED** (UC blocks the SQL Genie generates)
# MAGIC
# MAGIC The cell below grants the App SP what it needs:
# MAGIC
# MAGIC | Layer | Object | Privilege |
# MAGIC |---|---|---|
# MAGIC | UC | `<target_catalog>` | `USE CATALOG` |
# MAGIC | UC | `<target_catalog>.<target_schema>` | `USE SCHEMA` |
# MAGIC | UC | `<target_catalog>.<target_schema>.{departments, kpi_submissions, monthly_reporting_userbase}` | `SELECT` |
# MAGIC | Lakebase | `public` schema | `USAGE` |
# MAGIC | Lakebase | `public.{departments, kpi_submissions, monthly_reporting_userbase}` | `SELECT, INSERT, UPDATE, DELETE` |
# MAGIC | Lakebase | future tables in `public` | Same DML via `ALTER DEFAULT PRIVILEGES` |

# COMMAND ----------

from databricks.sdk import WorkspaceClient
from databricks.sdk.errors.platform import ResourceAlreadyExists

import psycopg
from databricks.sdk.service.catalog import PermissionsChange, Privilege

w = WorkspaceClient()

# The App's service principal client_id is also the Lakebase role name.
sp_client_id = w.apps.get(name=APP_NAME).service_principal_client_id
if not sp_client_id:
    raise ValueError(
        f"App {APP_NAME} has no service_principal_client_id yet — "
        "wait a few seconds for the App to finish provisioning and re-run."
    )
print(f"App SP: {sp_client_id}")

# Lakebase Postgres tables — these live in the `public` schema of the Lakebase DB
# (created/seeded by notebook 01). Used for the Lakebase GRANTs further below.
LAKEBASE_TABLES = ("departments", "kpi_submissions", "monthly_reporting_userbase")
# Unity Catalog objects the app/Genie read = the synced views PLUS kpi_targets and the
# kpi_metrics metric view (notebook 02). Genie needs SELECT on the metric view AND its
# source tables or queries fail with PERMISSION_DENIED. NOTE: kpi_targets/kpi_metrics
# are UC-only (they do NOT exist in Lakebase Postgres), so they're excluded from the
# Lakebase grants.
UC_TABLES = LAKEBASE_TABLES + ("kpi_targets", "kpi_metrics")

# --- Unity Catalog grants (so Genie can read the synced Delta views) ---
print(f"\nGranting Unity Catalog access on {TARGET_CATALOG}.{TARGET_SCHEMA}...")
w.grants.update(
    securable_type="catalog",
    full_name=TARGET_CATALOG,
    changes=[PermissionsChange(principal=sp_client_id, add=[Privilege.USE_CATALOG])],
)
w.grants.update(
    securable_type="schema",
    full_name=f"{TARGET_CATALOG}.{TARGET_SCHEMA}",
    changes=[PermissionsChange(principal=sp_client_id, add=[Privilege.USE_SCHEMA])],
)
for tbl in UC_TABLES:
    full = f"{TARGET_CATALOG}.{TARGET_SCHEMA}.{tbl}"
    try:
        w.grants.update(
            securable_type="table",
            full_name=full,
            changes=[PermissionsChange(principal=sp_client_id, add=[Privilege.SELECT])],
        )
        print(f"  SELECT on {full}")
    except Exception as e:
        print(f"  skipped {full}: {e}")

# --- Lakebase grants (so the app can read/write submissions) ---
print(f"\nGranting Lakebase access on project {LAKEBASE_PROJECT}...")
endpoint_path = f"projects/{LAKEBASE_PROJECT}/branches/production/endpoints/primary"
ep = w.postgres.get_endpoint(name=endpoint_path)
pg_host = ep.status.hosts.host

# Short-lived OAuth credential (used as the Postgres password) + current user,
# via the SDK — consistent with the get_endpoint call above (no raw REST / token).
pg_token = w.postgres.generate_database_credential(endpoint=endpoint_path).token
pg_user = w.current_user.me().user_name

conn_string = (
    f"host={pg_host} dbname=databricks_postgres user={pg_user} "
    f"password={pg_token} sslmode=require"
)
with psycopg.connect(conn_string) as conn:
    conn.autocommit = True
    with conn.cursor() as cur:
        cur.execute(f'GRANT USAGE ON SCHEMA public TO "{sp_client_id}"')
        for tbl in LAKEBASE_TABLES:
            cur.execute(f'GRANT SELECT, INSERT, UPDATE, DELETE ON public.{tbl} TO "{sp_client_id}"')
            print(f"  SELECT/INSERT/UPDATE/DELETE on public.{tbl}")
        # Make future tables auto-grant the same DML so re-running notebook 01
        # (which CREATE TABLE IF NOT EXISTSes new tables) doesn't lose access.
        cur.execute(
            f'ALTER DEFAULT PRIVILEGES IN SCHEMA public '
            f'GRANT SELECT, INSERT, UPDATE, DELETE ON TABLES TO "{sp_client_id}"'
        )

print("\nGrants applied — the App SP can now read UC views and read/write Lakebase tables.")

# COMMAND ----------

# MAGIC %md
# MAGIC ## Step 4 — Build & deploy the App (SDK)
# MAGIC
# MAGIC No `databricks bundle deploy` and no local build needed — this cell does
# MAGIC everything from the workspace:
# MAGIC 1. **Builds the app wheel** from this repo. The build is pure-Python
# MAGIC    (hatchling), so it runs right here on the cluster — it does **not** run
# MAGIC    the React/bun build. The compiled frontend
# MAGIC    (`src/kpi_reporting/__dist__`) is committed to the repo, and the wheel
# MAGIC    just packages it.
# MAGIC 2. Generates an `app.yml` from the widget values.
# MAGIC 3. Assembles a `.build/` folder next to this notebook (wheel +
# MAGIC    `requirements.txt` + `app.yml`).
# MAGIC 4. Triggers an Apps deployment pointing at that `.build/` path.
# MAGIC
# MAGIC > **Why we write `app.yml` directly**: the Apps deployment API accepts
# MAGIC > an `env_vars` field on `AppDeployment`, but in practice the Apps
# MAGIC > runtime reads env from `app.yml` in the deployed source — that's why
# MAGIC > generating `app.yml` from widgets is the reliable way to control
# MAGIC > the running config.
# MAGIC
# MAGIC | Env var | Source |
# MAGIC |---|---|
# MAGIC | `KPI_REPORTING_LAKEBASE_PROJECT` | widget literal |
# MAGIC | `GENIE_SPACE_ID` | resource alias `genie_space` |
# MAGIC | `KPI_REPORTING_CONFLUENCE_*` | widget literals (only when Confluence enabled) |
# MAGIC | `KPI_REPORTING_CONFLUENCE_API_TOKEN` | resource alias `confluence_api_token` (only when Confluence enabled) |
# MAGIC | `PGHOST` / `PGUSER` / `ENDPOINT_NAME` | auto-injected by the postgres resource |
# MAGIC | `DATABRICKS_HOST` | auto-injected by the Apps runtime |
# MAGIC
# MAGIC > **Refreshing the source code**: if you change Python code, just re-run
# MAGIC > this cell. If you change **React/frontend** code, rebuild the compiled
# MAGIC > frontend locally with `uv run apx build` and commit
# MAGIC > `src/kpi_reporting/__dist__`, then re-run this cell.

# COMMAND ----------

import glob
import os
import shutil
import subprocess
import sys
import tempfile
from databricks.sdk.service.apps import AppDeployment
from databricks.sdk.service.workspace import ImportFormat

if ENABLE_CONFLUENCE:
    required = {
        "Confluence URL": CONFLUENCE_BASE_URL,
        "Confluence email": CONFLUENCE_USER_EMAIL,
        "Confluence space key": CONFLUENCE_SPACE_KEY,
        "Confluence parent page ID": CONFLUENCE_PARENT_PAGE_ID,
    }
    missing = [k for k, v in required.items() if not v or v.startswith("https://your-org")]
    if missing:
        raise ValueError(f"Set these widgets before deploying: {missing}")

# Derive paths from the notebook's own path. The repo (this Git folder / synced
# files) and the .build/ we assemble live under the same parent.
# notebookPath() returns "/Users/..."; FUSE + the Apps API need "/Workspace/Users/...".
nb_path = dbutils.notebook.entry_point.getDbutils().notebook().getContext().notebookPath().get()
files_root = nb_path.rsplit("/notebooks/", 1)[0]
if not files_root.startswith("/Workspace/"):
    files_root = f"/Workspace{files_root}"
repo_fuse = files_root            # repo root, readable on the driver via the /Workspace mount
source_path = f"{files_root}/.build"
print(f"Repo:   {repo_fuse}")
print(f"Source: {source_path}")

# --- Build the app wheel (pure Python — no Node/bun) -----------------------
# Copy the repo to local disk and build with hatchling. This packages the
# committed frontend (src/kpi_reporting/__dist__); it does NOT run the React
# build, so no Node/bun is required on the cluster.
build_src = tempfile.mkdtemp(prefix="kpi_build_")
shutil.rmtree(build_src, ignore_errors=True)
shutil.copytree(
    repo_fuse, build_src,
    ignore=shutil.ignore_patterns(".git", "node_modules", ".venv", ".build", "dist", "__pycache__"),
)
if not os.path.exists(os.path.join(build_src, "src", "kpi_reporting", "__dist__", "index.html")):
    raise FileNotFoundError(
        "src/kpi_reporting/__dist__ is missing — the compiled frontend must be "
        "committed to the repo. Run `uv run apx build` locally and commit it."
    )
subprocess.run(
    [sys.executable, "-m", "pip", "install", "-q", "build", "hatchling", "uv-dynamic-versioning"],
    check=True,
)
# --no-isolation: build with the deps we just installed (no PyPI round trip).
subprocess.run(
    [sys.executable, "-m", "build", "--wheel", "--no-isolation", build_src],
    check=True,
)
wheel_path = sorted(glob.glob(os.path.join(build_src, "dist", "*.whl")))[-1]
wheel_name = os.path.basename(wheel_path)
print(f"Built wheel: {wheel_name}")

# Build app.yml content from widget values.
def _esc(s):
    # YAML double-quoted scalar — escape backslashes and double quotes.
    return '"' + str(s).replace("\\", "\\\\").replace('"', '\\"') + '"'

env_lines = [
    f"  - name: KPI_REPORTING_LAKEBASE_PROJECT\n    value: {_esc(LAKEBASE_PROJECT)}",
    "  - name: GENIE_SPACE_ID\n    valueFrom: genie_space",
]
if ENABLE_CONFLUENCE:
    env_lines.extend([
        f"  - name: KPI_REPORTING_CONFLUENCE_BASE_URL\n    value: {_esc(CONFLUENCE_BASE_URL)}",
        f"  - name: KPI_REPORTING_CONFLUENCE_USER_EMAIL\n    value: {_esc(CONFLUENCE_USER_EMAIL)}",
        f"  - name: KPI_REPORTING_CONFLUENCE_SPACE_KEY\n    value: {_esc(CONFLUENCE_SPACE_KEY)}",
        f"  - name: KPI_REPORTING_CONFLUENCE_PARENT_PAGE_ID\n    value: {_esc(CONFLUENCE_PARENT_PAGE_ID)}",
        "  - name: KPI_REPORTING_CONFLUENCE_API_TOKEN\n    valueFrom: confluence_api_token",
    ])

app_yml_content = (
    'command: ["uvicorn", "kpi_reporting.backend.app:app", "--workers", "2"]\n'
    "env:\n"
    + "\n".join(env_lines)
    + "\n"
)
print(f"Confluence: {'enabled' if ENABLE_CONFLUENCE else 'disabled'}")
print("\n--- generated app.yml ---")
print(app_yml_content)

# --- Assemble .build/ in the workspace -------------------------------------
# Upload the wheel (binary), a requirements.txt that references it, and the
# generated app.yml. ImportFormat.AUTO stores the .whl as a workspace file.
with open(wheel_path, "rb") as f:
    wheel_bytes = f.read()
w.workspace.mkdirs(source_path)
w.workspace.upload(
    path=f"{source_path}/{wheel_name}", content=wheel_bytes,
    format=ImportFormat.AUTO, overwrite=True,
)
w.workspace.upload(
    path=f"{source_path}/requirements.txt", content=(wheel_name + "\n").encode("utf-8"),
    format=ImportFormat.AUTO, overwrite=True,
)
w.workspace.upload(
    path=f"{source_path}/app.yml", content=app_yml_content.encode("utf-8"),
    format=ImportFormat.AUTO, overwrite=True,
)
print(f"Wrote {source_path}/  ({wheel_name}, requirements.txt, app.yml)")

# Trigger app deploy. Env vars come from the app.yml we just uploaded.
deployment = AppDeployment(source_code_path=source_path)
print(f"\nDeploying {APP_NAME} (this can take a couple of minutes)...")
result = w.apps.deploy_and_wait(app_name=APP_NAME, app_deployment=deployment)
print(f"Deployment ID: {result.deployment_id}")
print(f"Status: {result.status.state if result.status else '?'}")
print(f"Message: {result.status.message if result.status else '?'}")

app_info = w.apps.get(name=APP_NAME)
print(f"\nApp URL: {app_info.url}")

# COMMAND ----------

# MAGIC %md
# MAGIC ## Step 5 — Smoke test
# MAGIC
# MAGIC 1. Open the App URL → SSO redirect → dashboard
# MAGIC 2. Sidebar shows your name + role from the userbase
# MAGIC 3. **Submission view** — pick a region/period, edit a justification, save, lock
# MAGIC 4. **Executive dashboard** → Genie chat. Try:
# MAGIC    - *"Which region has the highest Operating Margin in Jan 2026?"*
# MAGIC    - SQL + result table comes back
# MAGIC 5. **Publish to Confluence** on a submission — page appears under your parent page

# COMMAND ----------

# MAGIC %md
# MAGIC ## Troubleshooting
# MAGIC
# MAGIC | Symptom | Likely cause |
# MAGIC |---|---|
# MAGIC | App returns 500 on `/api/me` | Userbase doesn't include the logged-in email — add a row to `monthly_reporting_userbase` in notebook 01 |
# MAGIC | App falls back to mock data | Lakebase resource not attached or `PGHOST`/`PGUSER` not injected — re-run Step 3 |
# MAGIC | App boots but env vars look empty (e.g. `KPI_REPORTING_LAKEBASE_PROJECT=None`) | The `app.yml` Step 4 generated didn't reach the App — re-run Step 4 to regenerate `app.yml` from your widgets and redeploy. |
# MAGIC | `ModuleNotFoundError: No module named 'kpi_reporting'` after deploy | The wheel was built with `src/kpi_reporting/...` paths instead of `kpi_reporting/...` at the root. Make sure `pyproject.toml` has `[tool.hatch.build.targets.wheel] packages = ["src/kpi_reporting"]`. |
# MAGIC | `FileNotFoundError: src/kpi_reporting/__dist__ is missing` in Step 4 | The compiled frontend isn't committed. Run `uv run apx build` locally, commit `src/kpi_reporting/__dist__`, and pull the repo into the workspace. |
# MAGIC | Step 4 build fails installing `build`/`hatchling` | The cluster has no internet egress to PyPI — use a cluster/serverless with PyPI access, or pre-install `build hatchling uv-dynamic-versioning`. |
# MAGIC | Genie chat returns *Query ended with status: FAILED* | The App's service principal doesn't have `SELECT` on the synced Delta views — re-run Step 3b to apply UC grants. |
# MAGIC | Submission edits don't show up in Lakebase | The App SP doesn't have `INSERT/UPDATE/DELETE` on the Lakebase tables — re-run Step 3b to apply Lakebase grants. |
# MAGIC | Genie chat returns *Genie Space not configured* | `GENIE_SPACE_ID` not set — confirm the resource alias is `genie_space` (Step 3) |
# MAGIC | Genie Space shows no data | Lakebase CDF not active or tables not added to the Space — see notebook 02 + Step 1 |
# MAGIC | Publish-to-Confluence returns 401 | Wrong email/token — re-check Step 2 widgets + the secret stored in Step 2d |
# MAGIC | Publish-to-Confluence returns 404 | Wrong space key or parent page ID — re-check Step 2b widgets |
# MAGIC | `Source code path must be a valid workspace path` | The `.build/` path didn't get the `/Workspace/` prefix — make sure you're running this notebook from a workspace/Git folder, not a local checkout. |
# MAGIC
# MAGIC > **How source code is packaged**: Step 4 builds the wheel on the cluster
# MAGIC > from the committed source (including `src/kpi_reporting/__dist__`) and
# MAGIC > assembles `.build/` in the workspace — no `databricks bundle deploy` and
# MAGIC > no local build are involved. To ship Python changes, just re-run Step 4;
# MAGIC > to ship frontend changes, rebuild `__dist__` locally with
# MAGIC > `uv run apx build`, commit it, and re-run Step 4.
