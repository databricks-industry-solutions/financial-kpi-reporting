"""Confluence REST API client for publishing KPI reports."""
import httpx
from .logger import logger


class ConfluenceClient:
    def __init__(self, base_url: str, api_token: str, user_email: str, space_key: str, parent_page_id: str = ""):
        self.base_url = base_url.rstrip("/")
        self.space_key = space_key
        self.parent_page_id = parent_page_id
        self._auth = (user_email, api_token)
        self._enabled = bool(base_url and api_token and user_email and space_key)

    @property
    def enabled(self) -> bool:
        return self._enabled

    def _build_kpi_page_html(self, submission: dict) -> str:
        locked_icon = "&#9989;" if submission.get("kpi_lockin") else "&#10060;"
        gm = submission.get("reviewed_by_gm") or "Not yet reviewed"

        fields = [
            ("Key Drivers (Quantitative)", submission.get("key_drivers_quantitative", "")),
            ("Key Drivers (Qualitative)", submission.get("key_drivers_qualitative", "")),
            ("Internal Factors", submission.get("internal_factors", "")),
            ("External Factors", submission.get("external_factors", "")),
            ("One-off Events", submission.get("oneoff_events", "")),
            ("Planned Actions", submission.get("planned_actions", "")),
            ("Expected Impact", submission.get("expected_impact", "")),
            ("Sentiment", submission.get("sentiment_tags", "")),
        ]

        rows_html = ""
        for label, value in fields:
            display = value if value else "<em>Not provided</em>"
            rows_html += f"<tr><td><strong>{label}</strong></td><td>{display}</td></tr>"

        return f"""
        <h2>Monthly KPI Report: {submission['kpi_name']}</h2>
        <ac:structured-macro ac:name="info">
            <ac:rich-text-body>
                <p><strong>Region:</strong> {submission['department_name']} | <strong>Period:</strong> {submission['period']} | <strong>Category:</strong> {submission.get('kpi_category', '')}</p>
            </ac:rich-text-body>
        </ac:structured-macro>
        <table>
            <tr><th>Field</th><th>Details</th></tr>
            <tr><td><strong>KPI</strong></td><td>{submission['kpi_name']} (#{submission.get('kpi_number', '')})</td></tr>
            {rows_html}
            <tr><td><strong>Locked In</strong></td><td>{locked_icon}</td></tr>
            <tr><td><strong>Reviewed by GM</strong></td><td>{gm}</td></tr>
            <tr><td><strong>Submitted By</strong></td><td>{submission.get('submitted_by', '')}</td></tr>
        </table>
        """

    async def _find_page_by_title(self, client: httpx.AsyncClient, title: str) -> dict | None:
        resp = await client.get(
            f"{self.base_url}/rest/api/content",
            auth=self._auth,
            params={"spaceKey": self.space_key, "title": title, "type": "page"},
        )
        resp.raise_for_status()
        results = resp.json().get("results", [])
        return results[0] if results else None

    async def _update_page(self, client: httpx.AsyncClient, page_id: str, title: str, body: str) -> httpx.Response:
        get_resp = await client.get(
            f"{self.base_url}/rest/api/content/{page_id}",
            auth=self._auth,
        )
        get_resp.raise_for_status()
        current_version = get_resp.json()["version"]["number"]

        return await client.put(
            f"{self.base_url}/rest/api/content/{page_id}",
            auth=self._auth,
            json={
                "version": {"number": current_version + 1},
                "title": title,
                "type": "page",
                "body": {
                    "storage": {"value": body, "representation": "storage"}
                },
            },
        )

    def _build_submissions_summary_html(self, submissions: list[dict], department_name: str, period: str | None) -> str:
        total = len(submissions)
        filled = sum(1 for s in submissions if any(
            s.get(f) for f in ("key_drivers_quantitative", "key_drivers_qualitative", "internal_factors", "external_factors", "planned_actions", "expected_impact")
        ))
        locked = sum(1 for s in submissions if s.get("kpi_lockin"))
        gm_reviewed = sum(1 for s in submissions if s.get("reviewed_by_gm"))

        period_text = period if period else "All Periods"

        rows_html = ""
        for s in submissions:
            is_filled = any(s.get(f) for f in ("key_drivers_quantitative", "key_drivers_qualitative", "internal_factors", "external_factors"))
            fill_icon = "&#9989;" if is_filled else "&#10060;"
            lock_icon = "&#128274;" if s.get("kpi_lockin") else "—"
            gm_icon = s.get("reviewed_by_gm") or "—"
            rows_html += f"""<tr>
                <td>{s['period']}</td>
                <td>{s['kpi_name']}</td>
                <td>{s.get('kpi_category', '')}</td>
                <td>{fill_icon}</td>
                <td>{lock_icon}</td>
                <td>{gm_icon}</td>
                <td>{s.get('sentiment_tags', '')}</td>
            </tr>"""

        return f"""
        <h2>Monthly KPI Report — {department_name}</h2>
        <ac:structured-macro ac:name="info">
            <ac:rich-text-body>
                <p><strong>Period:</strong> {period_text} | <strong>Total KPIs:</strong> {total}</p>
            </ac:rich-text-body>
        </ac:structured-macro>
        <h3>Completion Overview</h3>
        <table>
            <tr><th>Metric</th><th>Value</th></tr>
            <tr><td>Total KPI Entries</td><td>{total}</td></tr>
            <tr><td>Filled In</td><td><strong>{filled}</strong> ({round(filled/total*100) if total else 0}%)</td></tr>
            <tr><td>Locked In</td><td><strong>{locked}</strong></td></tr>
            <tr><td>GM Reviewed</td><td><strong>{gm_reviewed}</strong></td></tr>
        </table>
        <h3>KPI Details</h3>
        <table>
            <tr><th>Period</th><th>KPI</th><th>Category</th><th>Filled</th><th>Locked</th><th>GM Review</th><th>Sentiment</th></tr>
            {rows_html}
        </table>
        """

    def _build_dashboard_summary_html(self, summary: dict, dept_stats: list[dict], period: str | None) -> str:
        period_text = period if period else "All Periods"

        dept_rows = ""
        for d in dept_stats:
            fill_pct = d["fill_rate"]
            color = "#00875A" if fill_pct >= 80 else "#FF8B00" if fill_pct >= 50 else "#DE350B"
            dept_rows += f"""<tr>
                <td>{d['name']}</td>
                <td>{d['lead_name']}</td>
                <td>{d['kpi_count']}</td>
                <td>{d['filled']}</td>
                <td>{d['locked']}</td>
                <td><span style="color: {color}; font-weight: bold;">{fill_pct}%</span></td>
            </tr>"""

        return f"""
        <h2>Monthly KPI Report — Executive Summary</h2>
        <ac:structured-macro ac:name="info">
            <ac:rich-text-body>
                <p><strong>Period:</strong> {period_text}</p>
            </ac:rich-text-body>
        </ac:structured-macro>
        <h3>Key Metrics</h3>
        <table>
            <tr><th>Metric</th><th>Value</th></tr>
            <tr><td>Total KPI Entries</td><td>{summary['total_entries']}</td></tr>
            <tr><td>Filled In</td><td><strong>{summary['filled_entries']}</strong></td></tr>
            <tr><td>Locked In</td><td>{summary['locked_entries']}</td></tr>
            <tr><td>GM Reviewed</td><td>{summary['gm_reviewed_entries']}</td></tr>
            <tr><td>Centers Reporting</td><td>{summary['departments_reporting']}</td></tr>
        </table>
        <h3>Region Overview</h3>
        <table>
            <tr><th>Region</th><th>Lead</th><th>Total KPIs</th><th>Filled</th><th>Locked</th><th>Fill Rate</th></tr>
            {dept_rows}
        </table>
        """

    def _build_risk_report_html(self, report: dict) -> str:
        """Render an AI risk report (dict form of RiskReport) to Confluence storage HTML."""
        import html as _html

        def esc(v):
            return _html.escape(str(v or ""))

        period = esc(report.get("period"))
        generated_at = esc(report.get("generated_at", ""))[:10]

        sev_color = {"high": "#DE350B", "medium": "#FF8B00", "low": "#0052CC"}
        sent_color = {
            "positive": "#00875A", "neutral": "#6B778C",
            "cautious": "#FF8B00", "negative": "#DE350B",
        }

        # Top risks
        risk_rows = ""
        for r in report.get("top_risks", []):
            sev = str(r.get("severity", "low")).lower()
            color = sev_color.get(sev, "#0052CC")
            ccs = ", ".join(esc(c) for c in r.get("affected_regions", []))
            kpis = ", ".join(esc(k) for k in r.get("affected_kpis", []))
            risk_rows += f"""<tr>
                <td><strong>{r.get('rank', '')}</strong></td>
                <td><span style="color: {color}; font-weight: bold; text-transform: uppercase;">{esc(sev)}</span></td>
                <td><strong>{esc(r.get('title'))}</strong><br/><em>{esc(r.get('evidence'))}</em></td>
                <td>{ccs}<br/><em>{kpis}</em></td>
                <td>{esc(r.get('recommended_action'))}</td>
            </tr>"""

        # Region summaries
        cc_rows = ""
        for cc in report.get("region_summaries", []):
            sent = str(cc.get("overall_sentiment", "neutral")).lower()
            color = sent_color.get(sent, "#6B778C")
            cc_rows += f"""<tr>
                <td><strong>{esc(cc.get('region_name'))}</strong></td>
                <td><span style="color: {color}; font-weight: bold; text-transform: capitalize;">{esc(sent)}</span></td>
                <td style="text-transform: capitalize;">{esc(cc.get('risk_level'))}</td>
                <td>{esc(cc.get('headline'))}</td>
            </tr>"""

        return f"""
        <ac:structured-macro ac:name="info">
            <ac:rich-text-body>
                <p><strong>AI-Generated Risk &amp; Sentiment Report</strong> &#8212; Period: {period} &#183; Generated: {generated_at}</p>
            </ac:rich-text-body>
        </ac:structured-macro>

        <h2>Executive Summary</h2>
        <p>{esc(report.get('executive_summary'))}</p>

        <h2>Top Risks</h2>
        <table>
            <tr><th>#</th><th>Severity</th><th>Risk &amp; Evidence</th><th>Affected</th><th>Recommended Action</th></tr>
            {risk_rows}
        </table>

        <h2>Region Summaries</h2>
        <table>
            <tr><th>Region</th><th>Sentiment</th><th>Risk Level</th><th>Headline</th></tr>
            {cc_rows}
        </table>

        <h2>Cross-Cutting Patterns</h2>
        <p>{esc(report.get('cross_cutting_patterns'))}</p>

        <h2>Outlook</h2>
        <p>{esc(report.get('outlook'))}</p>
        """

    async def publish_page(self, title: str, body: str) -> dict:
        if not self._enabled:
            raise RuntimeError("Confluence integration is not configured")

        async with httpx.AsyncClient() as client:
            existing = await self._find_page_by_title(client, title)
            if existing:
                resp = await self._update_page(client, existing["id"], title, body)
            else:
                create_payload = {
                    "type": "page",
                    "title": title,
                    "space": {"key": self.space_key},
                    "body": {"storage": {"value": body, "representation": "storage"}},
                }
                if self.parent_page_id:
                    create_payload["ancestors"] = [{"id": self.parent_page_id}]
                resp = await client.post(
                    f"{self.base_url}/rest/api/content",
                    auth=self._auth,
                    json=create_payload,
                )
                if resp.status_code in (400, 404, 409):
                    found = await self._find_page_by_title(client, title)
                    if found:
                        resp = await self._update_page(client, found["id"], title, body)
                    else:
                        resp.raise_for_status()

            resp.raise_for_status()
            data = resp.json()
            page_id = data["id"]
            page_url = f"{data['_links']['base']}{data['_links']['webui']}"
            logger.info(f"Published Confluence page: {page_id}")
            return {"confluence_page_id": page_id, "confluence_page_url": page_url}

    async def publish_submission(self, submission: dict, existing_page_id: str | None = None) -> dict:
        if not self._enabled:
            raise RuntimeError("Confluence integration is not configured")

        title = f"Monthly KPI — {submission['kpi_name']} — {submission['department_name']} — {submission['period']}"
        body = self._build_kpi_page_html(submission)

        async with httpx.AsyncClient() as client:
            if existing_page_id:
                resp = await self._update_page(client, existing_page_id, title, body)
            else:
                create_payload = {
                    "type": "page",
                    "title": title,
                    "space": {"key": self.space_key},
                    "body": {
                        "storage": {"value": body, "representation": "storage"}
                    },
                }
                if self.parent_page_id:
                    create_payload["ancestors"] = [{"id": self.parent_page_id}]

                resp = await client.post(
                    f"{self.base_url}/rest/api/content",
                    auth=self._auth,
                    json=create_payload,
                )

                if resp.status_code in (400, 404, 409):
                    existing = await self._find_page_by_title(client, title)
                    if existing:
                        logger.info(f"Page with title already exists ({existing['id']}), updating")
                        resp = await self._update_page(client, existing["id"], title, body)
                    else:
                        resp.raise_for_status()

            resp.raise_for_status()
            data = resp.json()
            page_id = data["id"]
            page_url = f"{data['_links']['base']}{data['_links']['webui']}"
            logger.info(f"Published Confluence page: {page_id}")

            return {"confluence_page_id": page_id, "confluence_page_url": page_url}
