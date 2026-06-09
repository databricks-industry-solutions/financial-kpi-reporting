"""Lakebase client with connection pooling and token refresh."""
import time
import uuid as _uuid
from datetime import datetime, date
from urllib.parse import quote_plus
from databricks.sdk import WorkspaceClient
from sqlalchemy import create_engine, text
from sqlalchemy.pool import QueuePool
from .logger import logger


def _serialize_row(row: dict) -> dict:
    """Convert non-JSON-native types (UUID, datetime) to strings."""
    out = {}
    for k, v in row.items():
        if isinstance(v, _uuid.UUID):
            out[k] = str(v)
        elif isinstance(v, (datetime, date)):
            out[k] = v.isoformat()
        else:
            out[k] = v
    return out


_FILL_FIELDS = (
    "key_drivers_quantitative", "key_drivers_qualitative",
    "internal_factors", "external_factors",
    "planned_actions", "expected_impact",
)


class LakebaseClient:
    """Client for Lakebase Autoscale PostgreSQL.

    Supports two modes:
    1. App resource (preferred): PGHOST/PGUSER/ENDPOINT_NAME injected by
       Databricks Apps resource. OAuth tokens are generated per-connection.
    2. Native PG credentials: static host/user/password (e.g. for local dev).
    """

    def __init__(self, project_id: str, pg_host: str = "", pg_user: str = "",
                 pg_password: str = "", pg_endpoint_name: str = ""):
        self.project_id = project_id
        self._pg_host = pg_host
        self._pg_user = pg_user
        self._pg_password = pg_password
        self._pg_endpoint_name = pg_endpoint_name
        self._engine = None
        self._token_expires = 0
        self._ws = WorkspaceClient()

    def _get_oauth_password(self) -> str:
        """Generate a fresh OAuth token for Lakebase authentication."""
        endpoint = self._pg_endpoint_name or f"projects/{self.project_id}/branches/production/endpoints/primary"
        cred = self._ws.postgres.generate_database_credential(endpoint=endpoint)
        return cred.token

    def _refresh_engine(self):
        """Create/refresh SQLAlchemy engine."""
        now = time.time()
        if self._engine and now < self._token_expires:
            return

        if self._pg_host and self._pg_user and self._pg_password:
            # Static native PG credentials (local dev)
            url = f"postgresql+psycopg://{quote_plus(self._pg_user)}:{quote_plus(self._pg_password)}@{self._pg_host}/databricks_postgres?sslmode=require"
            self._engine = create_engine(url, poolclass=QueuePool, pool_size=5, pool_recycle=1800)
            self._token_expires = now + 86400
            logger.info(f"Lakebase engine created with native PG credentials (user={self._pg_user})")
        elif self._pg_host and self._pg_user:
            # App resource: host+user injected, generate OAuth token
            token = self._get_oauth_password()
            url = f"postgresql+psycopg://{quote_plus(self._pg_user)}:{quote_plus(token)}@{self._pg_host}/databricks_postgres?sslmode=require"
            self._engine = create_engine(url, poolclass=QueuePool, pool_size=5, pool_recycle=1800)
            self._token_expires = now + 3000  # refresh before 1h expiry
            logger.info(f"Lakebase engine created via app resource (host={self._pg_host}, user={self._pg_user})")
        else:
            # Fallback: resolve endpoint from project ID
            endpoint_name = f"projects/{self.project_id}/branches/production/endpoints/primary"
            ep = self._ws.postgres.get_endpoint(name=endpoint_name)
            host = ep.status.hosts.host
            token = self._get_oauth_password()
            username = self._ws.config.client_id or self._ws.current_user.me().user_name
            url = f"postgresql+psycopg://{quote_plus(username)}:{quote_plus(token)}@{host}/databricks_postgres?sslmode=require"
            self._engine = create_engine(url, poolclass=QueuePool, pool_size=5, pool_recycle=1800)
            self._token_expires = now + 3000
            logger.info(f"Lakebase engine refreshed (OAuth fallback, host={host})")

    def execute(self, query: str, params: dict | None = None) -> list[dict]:
        """Execute a query and return results as list of dicts."""
        self._refresh_engine()
        with self._engine.connect() as conn:
            result = conn.execute(text(query), params or {})
            rows = [_serialize_row(dict(row._mapping)) for row in result.fetchall()] if result.returns_rows else []
            conn.commit()
            return rows

    # --- Userbase ---

    def get_userbase_entry(self, email: str) -> dict | None:
        rows = self.execute(
            "SELECT * FROM monthly_reporting_userbase WHERE employee_business_email = :email",
            {"email": email},
        )
        return rows[0] if rows else None

    # --- Departments ---

    def get_departments(self) -> list[dict]:
        return self.execute("SELECT * FROM departments ORDER BY name")

    def get_department(self, dept_id: str) -> dict | None:
        rows = self.execute("SELECT * FROM departments WHERE id = :id", {"id": dept_id})
        return rows[0] if rows else None

    # --- Submissions ---

    def get_submissions(
        self,
        department_id: str | None = None,
        period: str | None = None,
    ) -> list[dict]:
        conditions = []
        params: dict = {}

        if department_id:
            conditions.append("department_id = :department_id")
            params["department_id"] = department_id
        if period:
            conditions.append("period = :period")
            params["period"] = period

        where = f" WHERE {' AND '.join(conditions)}" if conditions else ""
        query = f"SELECT * FROM kpi_submissions{where} ORDER BY period, kpi_number"
        return self.execute(query, params)

    def get_submission(self, sub_id: str) -> dict | None:
        rows = self.execute("SELECT * FROM kpi_submissions WHERE id = :id", {"id": sub_id})
        return rows[0] if rows else None

    def update_submission(self, sub_id: str, data: dict) -> dict | None:
        sets = []
        params = {"id": sub_id}
        for key, value in data.items():
            if value is not None:
                sets.append(f"{key} = :{key}")
                params[key] = value
        if not sets:
            return self.get_submission(sub_id)
        sets.append("updated_at = NOW()")
        query = f"UPDATE kpi_submissions SET {', '.join(sets)} WHERE id = :id RETURNING *"
        rows = self.execute(query, params)
        return rows[0] if rows else None

    def update_submission_confluence(self, sub_id: str, page_id: str, page_url: str) -> dict | None:
        rows = self.execute(
            "UPDATE kpi_submissions SET confluence_page_id = :page_id, confluence_page_url = :page_url, updated_at = NOW() WHERE id = :id RETURNING *",
            {"id": sub_id, "page_id": page_id, "page_url": page_url},
        )
        return rows[0] if rows else None

    # --- Dashboard ---

    @staticmethod
    def _is_filled(row: dict) -> bool:
        return any(row.get(f) for f in _FILL_FIELDS)

    def get_dashboard_summary(self, period: str | None = None) -> dict:
        subs = self.get_submissions(period=period)
        total = len(subs)
        if total == 0:
            return {"total_entries": 0, "filled_entries": 0, "locked_entries": 0, "gm_reviewed_entries": 0, "departments_reporting": 0}

        filled = sum(1 for s in subs if self._is_filled(s))
        locked = sum(1 for s in subs if s.get("kpi_lockin"))
        gm_reviewed = sum(1 for s in subs if s.get("reviewed_by_gm"))
        departments_reporting = len(set(s["department_id"] for s in subs if self._is_filled(s)))

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
        filled = sum(1 for s in subs if self._is_filled(s))
        locked = sum(1 for s in subs if s.get("kpi_lockin"))
        fill_rate = round((filled / total) * 100, 1) if total > 0 else 0
        lock_rate = round((locked / total) * 100, 1) if total > 0 else 0

        return {
            "department": dept,
            "submissions": subs,
            "fill_rate": fill_rate,
            "lock_rate": lock_rate,
            "kpi_count": total,
        }
