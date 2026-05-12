# Security Policy

## Data Handling

**Synthetic data only.** This is a reference implementation demo. The repository and notebooks use randomly-generated synthetic KPI data matching the schema of a real financial reporting system. No actual financial data is included.

When deployed to your workspace, the application handles real data (KPI submissions, departmental targets, user records, and Confluence publications). Security practices for production data are your responsibility — see **Access Control** and **Production Deployment** below.

## Environment Variables & Secrets Management

All sensitive configuration is environment-variable driven. **Never commit secrets** (API tokens, database passwords, endpoints) to the repository.

### Local Development
- Copy `.env.example` to `.env` and fill in your credentials
- `.env` is in `.gitignore` — changes are never committed
- The backend falls back to in-memory mock data if Lakebase env vars are missing, allowing full UI testing without external credentials

### Deployed on Databricks Apps
- All environment variables are set at deploy time via notebook 03 (`notebooks/03_deploy_app.py`)
- The app runtime does not have access to the source code or `.env` file
- Databricks manages secret scope access — app code retrieves credentials via Pydantic Settings, never from filesystem or source

## Access Control

### Application Layer
The app implements a **trust-based access model**:
- User identity comes from Databricks OAuth (automatic, built into Apps platform)
- Regional leads see **only their region's KPI submissions**
- CFO sees **all regions**
- Role assignment is based on email domain matching (`notebooks/01_setup_lakebase.py`, `DEPARTMENTS` mapping)

**For production:** Implement row-level security (RLS) in Lakebase queries or Unity Catalog fine-grained access control to prevent unauthorized data leakage.

### Lakebase Project
- Databricks service principal credentials are injected at app deploy time
- Only the app service principal can connect to the Lakebase project
- Workspace users cannot access the project directly unless explicitly granted

### Confluence (Optional)
- Confluence API tokens are stored in Databricks secret scope
- The backend proxies all Confluence requests — credentials never reach the browser
- Publishing is idempotent by page title to prevent duplicates

## Known Limitations

1. **Role-based filtering is not row-level secure.** The backend trusts the userbase mapping for regional visibility. In a production system, validate this against Unity Catalog fine-grained access control or implement SQL-level RLS in Lakebase.

2. **No audit logging.** KPI submissions are stored in Lakebase but changes are not logged. For compliance-sensitive environments, add Databricks audit logs or Delta change feed tracking.

3. **Confluence is optional and unencrypted in transit by default.** If publishing to Confluence, ensure your workspace can reach the Confluence Cloud instance over HTTPS.

4. **Genie data access.** The Genie Space is created with default permissions. In a production Genie deployment, configure space membership to control who can access the AI chat interface.

5. **No credential rotation.** API tokens for Lakebase, Genie, and Confluence are managed manually. For production, consider rotating credentials periodically and use Databricks service principal OAuth where available.

## Dependencies

See `pyproject.toml` and `package.json` for the full dependency list. Key dependencies:

- **FastAPI** — REST API framework, actively maintained
- **Pydantic** — Data validation; used for environment variable loading
- **SQLAlchemy + psycopg** — Lakebase client libraries
- **Databricks SDK** — Workspace API and auth
- **React 19** — Frontend framework

### Vulnerability Reporting

If you find a security vulnerability in this reference implementation:

1. **Do not open a public issue.** Instead, email security@databricks.com with details:
   - Vulnerability description
   - Affected version (if applicable)
   - Steps to reproduce (if applicable)

2. Databricks will acknowledge your report and work with you to understand the impact.

3. If a patch is released, Databricks will coordinate with you on disclosure timing.

### Security Review Checklist for Customization

When adapting this demo for your organization, review:

- [ ] User authentication: Is OAuth/SAML set up correctly for your SSO?
- [ ] Data access: Are regional roles enforced at the database level, not just the app?
- [ ] Secrets management: Are all API tokens, database passwords, and service principal keys in Databricks secret scopes or managed externally?
- [ ] Logging: Is audit trail enabled in Databricks workspace and Lakebase?
- [ ] Network: Can your workspace reach Lakebase, Genie, and Confluence (if enabled) over secure channels?
- [ ] Compliance: Does the deployment meet your data residency, encryption, and retention policies?

## Responsible Disclosure

If you discover a security issue in your deployment of this code, follow your organization's incident response procedures. If the issue is in the reference implementation itself, please report it as described above.

---

**Last updated:** 2026-05-07

