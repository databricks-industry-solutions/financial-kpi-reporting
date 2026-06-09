# Databricks notebook source
# MAGIC %md
# MAGIC # Teardown — delete every resource the demo created
# MAGIC
# MAGIC Reverses notebooks 01–03. Run this when you're done with the demo and
# MAGIC want to stop incurring Lakebase / Apps compute costs.
# MAGIC
# MAGIC **What this notebook removes:**
# MAGIC | Resource | Created in | Deleted by |
# MAGIC |---|---|---|
# MAGIC | App `kpi-reporting` (+ its service principal) | notebook 03 Step 3 | `w.apps.delete` |
# MAGIC | Lakebase project `kpi-reporting` (cascades to branches, databases, tables) | notebook 01 | `w.postgres.delete_project` |
# MAGIC | UC schema `<catalog>.<schema>` (Lakebase CDF [Change Data Feed, formerly "Lakehouse Sync"] history tables + clean views) | notebook 02 | Spark `DROP SCHEMA … CASCADE` |
# MAGIC | Genie Space (if you supply its ID) | notebook 03 Step 1 | `w.genie.trash_space` |
# MAGIC | Secret scope (only if Confluence was enabled) | notebook 03 Step 2d | `w.secrets.delete_scope` |
# MAGIC
# MAGIC **What this notebook does NOT remove (manual):**
# MAGIC - The bundle workspace files at `/Workspace/Users/<you>/financial-kpi-reporting/`
# MAGIC   — run `databricks bundle destroy` from your laptop to remove those.
# MAGIC
# MAGIC > **Read the widget values carefully before flipping `confirm` to `yes`.**
# MAGIC > This is irreversible; data and config are gone after a successful run.

# COMMAND ----------

# MAGIC %pip install -U "databricks-sdk>=0.74.0"
# MAGIC dbutils.library.restartPython()

# COMMAND ----------

# Create widgets — adjust their values via the toolbar at the top of the notebook
dbutils.widgets.dropdown("confirm", "no", ["no", "yes"], "Confirm DELETE (set to yes to run)")
dbutils.widgets.text("app_name", "kpi-reporting", "App name")
dbutils.widgets.text("lakebase_project", "kpi-reporting", "Lakebase project")
dbutils.widgets.text("target_catalog", "main", "Target catalog (notebook 02)")
dbutils.widgets.text("target_schema", "kpi_reporting", "Target schema (notebook 02)")
dbutils.widgets.text("secret_scope", "kpi-reporting", "Secret scope (only if Confluence was enabled)")
dbutils.widgets.text("genie_space_id", "", "Genie Space ID (optional — from the Genie URL; leave blank to skip)")

# COMMAND ----------

# Read widgets
CONFIRM = dbutils.widgets.get("confirm") == "yes"
APP_NAME = dbutils.widgets.get("app_name").strip()
LAKEBASE_PROJECT = dbutils.widgets.get("lakebase_project").strip()
TARGET_CATALOG = dbutils.widgets.get("target_catalog").strip()
TARGET_SCHEMA = dbutils.widgets.get("target_schema").strip()
SECRET_SCOPE = dbutils.widgets.get("secret_scope").strip()
GENIE_SPACE_ID = dbutils.widgets.get("genie_space_id").strip()

print(f"App:           {APP_NAME}")
print(f"Lakebase:      {LAKEBASE_PROJECT}")
print(f"UC schema:     {TARGET_CATALOG}.{TARGET_SCHEMA}")
print(f"Secret scope:  {SECRET_SCOPE}")
print(f"Genie Space:   {GENIE_SPACE_ID or '(blank — will skip)'}")
print(f"Confirm:       {'YES — will delete' if CONFIRM else 'no (dry run, no deletes)'}")

if not CONFIRM:
    print("\nFlip the `confirm` widget to `yes` and re-run to actually delete these resources.")
    dbutils.notebook.exit("dry-run — nothing deleted")

# COMMAND ----------

# MAGIC %md
# MAGIC ## Step 1 — Delete the App

# COMMAND ----------

from databricks.sdk import WorkspaceClient
from databricks.sdk.errors.platform import NotFound

w = WorkspaceClient()

try:
    app = w.apps.get(name=APP_NAME)
    print(f"Found {APP_NAME} (state={app.app_status.state if app.app_status else '?'})")
    try:
        w.apps.stop_and_wait(name=APP_NAME)
        print(f"Stopped {APP_NAME}")
    except Exception as e:
        print(f"  stop skipped ({type(e).__name__}: {e})")
    w.apps.delete(name=APP_NAME)
    print(f"Deleted app: {APP_NAME}")
except NotFound:
    print(f"App {APP_NAME} not found — nothing to delete.")

# COMMAND ----------

# MAGIC %md
# MAGIC ## Step 2 — Drop the UC schema (Lakebase CDF tables + views)

# COMMAND ----------

try:
    spark.sql(f"DROP SCHEMA IF EXISTS `{TARGET_CATALOG}`.`{TARGET_SCHEMA}` CASCADE")
    print(f"Dropped schema: {TARGET_CATALOG}.{TARGET_SCHEMA}")
except Exception as e:
    print(f"Schema drop failed: {e}")

# COMMAND ----------

# MAGIC %md
# MAGIC ## Step 3 — Delete the Lakebase project
# MAGIC
# MAGIC This cascades to all branches, databases, and tables under the project.

# COMMAND ----------

project_path = f"projects/{LAKEBASE_PROJECT}"
try:
    w.postgres.get_project(name=project_path)
    w.postgres.delete_project(name=project_path)
    print(f"Deleted Lakebase project: {LAKEBASE_PROJECT}")
except NotFound:
    print(f"Lakebase project {LAKEBASE_PROJECT} not found — nothing to delete.")
except Exception as e:
    print(f"Lakebase delete failed: {type(e).__name__}: {e}")

# COMMAND ----------

# MAGIC %md
# MAGIC ## Step 4 — Delete the secret scope (if it exists)

# COMMAND ----------

try:
    w.secrets.delete_scope(scope=SECRET_SCOPE)
    print(f"Deleted secret scope: {SECRET_SCOPE}")
except Exception as e:
    msg = str(e)
    if "does not exist" in msg.lower() or "not found" in msg.lower():
        print(f"Secret scope {SECRET_SCOPE} not found — nothing to delete.")
    else:
        print(f"Secret scope delete failed: {e}")

# COMMAND ----------

# MAGIC %md
# MAGIC ## Step 5 — Trash the Genie Space (if an ID was provided)
# MAGIC
# MAGIC Genie now has a public delete API (`w.genie.trash_space`), so this is no
# MAGIC longer a manual UI step. Supply the Space ID via the `genie_space_id` widget.

# COMMAND ----------

if not GENIE_SPACE_ID:
    print("No Genie Space ID provided — skipping. (Set the `genie_space_id` widget to delete it.)")
else:
    try:
        w.genie.trash_space(space_id=GENIE_SPACE_ID)
        print(f"Trashed Genie Space: {GENIE_SPACE_ID}")
    except NotFound:
        print(f"Genie Space {GENIE_SPACE_ID} not found — nothing to delete.")
    except Exception as e:
        print(f"Genie Space delete failed: {type(e).__name__}: {e}")

# COMMAND ----------

# MAGIC %md
# MAGIC ## Done
# MAGIC
# MAGIC Manual cleanup that's still required:
# MAGIC
# MAGIC 1. **Bundle workspace files** — from your laptop:
# MAGIC    ```bash
# MAGIC    databricks bundle destroy
# MAGIC    ```
# MAGIC    This removes `/Workspace/Users/<you>/financial-kpi-reporting/`,
# MAGIC    including this very notebook.
# MAGIC
# MAGIC > The Genie Space is now deleted by **Step 5** above (`w.genie.trash_space`)
# MAGIC > when you supply its ID — no manual UI step needed.

# COMMAND ----------

print("Teardown complete.")
