# Financial KPI Reporting — Explainer Video Outline

**Target Length:** 2-3 minutes  
**Audience:** Business leaders, FP&A teams, Databricks users  
**Format:** Screen recording + voiceover

---

## Scene 1: Problem Statement (0:00–0:15)

**Voiceover:** "Managing KPI submissions across multiple regions is complex. You need a single system where regional leaders can submit actuals and justifications, while executives see the consolidated picture and ask ad-hoc questions."

**Visual:** Show screenshot of regional KPI spreadsheet (messy, outdated)

---

## Scene 2: Regional Lead Workflow (0:15–0:45)

**Voiceover:** "Meet Alex Morgan, a regional leader. Each month, she logs into the KPI app to submit her region's KPI actuals."

**Actions:**
1. Login to app as Regional Lead (Alex Morgan)
2. Show the submission form: select month, region, enter KPI values (Revenue Growth, Operating Margin, DSO, OPEX Ratio, Free Cash Flow)
3. Add a qualitative note explaining variance (e.g., "Revenue up 15% due to new customer wins")
4. Lock the submission for review
5. Show success toast: "Submission locked for CFO review"

**Voiceover:** "She enters actuals, adds context, and locks the submission. It's now ready for leadership review."

---

## Scene 3: CFO Dashboard (0:45–1:30)

**Voiceover:** "Now meet Sam Carter, the CFO. She logs in to see the consolidated view across all 6 regions."

**Actions:**
1. Login as CFO (Sam Carter)
2. Show dashboard: 6-region KPI grid with color-coded performance (green/yellow/red)
3. Hover over a red cell (e.g., DSO trending up negatively)
4. Click to drill into that region's historical trend
5. Show the detail: month-by-month line chart + regional justification (Alex's note)
6. Go back to dashboard

**Voiceover:** "She sees the consolidated picture at a glance. Red cells highlight underperforming KPIs. She can drill into any region to see the trend and read the manager's justification."

---

## Scene 4: Genie Q&A (1:30–2:00)

**Voiceover:** "The best part? She can ask natural language questions about the data without writing SQL."

**Actions:**
1. Scroll to the Genie panel (embedded in the dashboard)
2. Type question: "Which regions have operating margin below 20%?"
3. Show Genie processing (spinning icon)
4. Show result: table with regions sorted by operating margin
5. Ask follow-up: "What's the trend for Free Cash Flow in the West region?"
6. Show chart result

**Voiceover:** "Genie answers instantly. She can explore the data however she wants."

---

## Scene 5: Under the Hood (2:00–2:20)

**Voiceover:** "Behind the scenes, this app combines Databricks' best practices: a React frontend for UX, a FastAPI backend for security, Lakebase for transactional KPI storage, and Unity Catalog for governed analytics."

**Visual:** Show the architecture diagram from README briefly

---

## Scene 6: Closing (2:20–2:30)

**Voiceover:** "Clone this reference implementation and customize it for your organization. Change departments, add your own KPIs, integrate your publishing target. It's production-ready."

**Visual:** Show GitHub repo URL / clone command

---

## Key Talking Points

- **Problem solved:** Single pane of glass for multi-unit KPI governance
- **Who it's for:** CFOs, FP&A teams, regional managers
- **Why it's great:** Combines submission form (Regional Lead) + executive dashboard (CFO) + natural-language AI (Genie)
- **Platform features:** Databricks Apps, Lakebase, UC, Genie, Lakehouse Sync
- **Customizable:** Swap departments, KPIs, publishing targets

---

## Recording Tips

1. **Speed:** Slow down slightly (2x speed is too fast for screen recordings)
2. **Cursor visibility:** Enable pointer/cursor visibility in screen recorder settings
3. **Background:** Mute notifications before recording
4. **Audio:** Record in quiet room; use desktop audio + mic
5. **Edits:** Add brief intro slide with title/date; add YouTube timestamp markers in description

---

## Suggested Tools

- **Screen recording:** OBS Studio (free), Loom (easy), or ScreenFlow (Mac)
- **Editing:** iMovie (Mac), DaVinci Resolve (free), or Premiere Pro
- **Hosting:** YouTube (unlisted), Loom, or internal video server
