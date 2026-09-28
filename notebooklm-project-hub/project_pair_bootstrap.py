from __future__ import annotations

import asyncio
import json

from multi_project_bootstrap import bootstrap_one

PROJECTS = [
    {
        "project": "production-program",
        "notebook_title": "HI-LEX - Programa de Producción",
        "sources": [
            {
                "title": "PRODUCTION_PROGRAM_PROJECT_RULES.md — Project Constitution v1",
                "content": """# HI-LEX PROGRAMA DE PRODUCCIÓN — PROJECT CONSTITUTION v1

ROLE
NotebookLM is the documentary analyst for the Programa de Producción product. ChatGPT + development/QA skills are the execution and validation layer.

CURRENT PRODUCT PRINCIPLES
- Preserve working business logic, source-data contracts, import flow, filters, roles, admin behavior and existing validated interactions before changing UX/UI.
- The application remains a static local/intranet SPA using HTML/CSS/JavaScript and Microsoft Edge/Chromium. Do not silently introduce React, Next.js, Vue, Angular, Node backend, npm/build dependencies or mandatory CDN dependencies.
- UI work must follow USER -> DECISION -> INFORMATION -> HIERARCHY -> VISUALIZATION -> INTERACTION.
- Tables remain a primary analytical surface. Distinguish clearly 0, blank, N/A, no data, not applicable, error and warning.
- Motion is allowed only when it explains change, relationship, selection, navigation, update, alert or result.
- Professional/premium means decision clarity and information density, not decoration.
- Source-data and production-week integrity take priority over visual polish.

CURRENT PRODUCT RECORD
- V3.13.2 CANDIDATA was physically tested by the user and is treated as the current stable/LKG baseline for future improvements.
- Preserve automatic consolidation of duplicates by Fecha + Parte + Cliente + Línea + WC without losing volume.
- Preserve the operational-calendar behavior where WK39-26 is the last production week of production year 2026 and WK40-27 begins the following production year.
- Preserve the unique-focus navigation behavior already physically validated unless a verified defect requires change.

GOVERNANCE
- Never silently promote an untested candidate to LKG.
- Separate verified behavior, design recommendation, hypothesis and future roadmap.
- For a release decision, require reproducible regression evidence and physical/browser validation for critical flows.
""",
            },
            {
                "title": "Evaluacion_Programa_Produccion_V3.11.12.md — Audit Snapshot",
                "content": """SOURCE TYPE: Curated snapshot from Evaluacion_Programa_Produccion_V3.11.12.md.
ROLE: Historical technical/functional audit that documents architecture, data integrity, defects and release-gate logic.

VERIFIED AUDIT CONTENT
- Static application with a shared engine between consultation and administration, cache/index infrastructure and reusable architecture.
- Audit evaluated JavaScript engine behavior with real loaded data and synthetic import transformations without modifying the original ZIP.
- 2024: 27,975 effective records, 49 weeks, volume 43,429,700.
- 2025: 63,886 effective records, 50 weeks, volume 47,789,570.
- 2026 at that audit point: 124,418 effective records, 33 weeks, volume 38,229,510.
- 216,279 total effective records across 132 year-week combinations.
- Weekly sums by part, line and block reconciled to weekly totals for all tested combinations.
- High-priority defects identified at that point included: invalid text volume could be omitted while import remained accepted; negative/fractional quantities required explicit business validation; backup validation was structurally weak; historic client grouping excluded records with missing client; and one filter synchronization scenario could silently broaden scope.
- The V3.11.12 audit gate for a NEW release was BLOCK, while explicitly noting that the then-current application could still function.

INTERPRETATION RULE
This is historical audit evidence. Do not assume a V3.11.12 defect still exists in a later LKG unless reproduced there.
""",
            },
            {
                "title": "Programa_Produccion_UI_UX_Contract.md — Industrial Product Design Rules",
                "content": """SOURCE TYPE: Curated product-design contract derived from the Programa de Producción UX/UI specification.

NON-NEGOTIABLES
- Do not initially change functional logic. Preserve data sources, calculations, import, filters, information, business structure, permissions, roles and working behavior.
- Prioritize HTML, CSS and JavaScript. Local/intranet execution in Edge/Chromium remains the target architecture.
- Existing modules include Dashboard, Programa, Production Planning Intelligence, Estabilidad, Bloques, Líneas, Partes, Clientes and Admin/Data Center.
- Do not choose a chart because it is attractive. Choose based on Business Question + Data Shape + Audience + Decision + Risk + Density.
- Candidate industrial visual patterns include stability matrix, plan-vs-actual, production horizon, exception timeline, week-to-week variation, volume anomalies, line-health matrix, workload/trend/utilization, block contribution and stability heatmaps.
- Avoid KPI-card overload. Prefer primary signal -> context -> evidence -> action.
- Tables must support readable density, numeric alignment, grouping hierarchy, filtering/search/sorting, status/alert markers and clear zero-vs-blank semantics.
""",
            },
            {
                "title": "Programa_Produccion_Operational_Data_2026-09-25.md — Weekly Data Snapshot",
                "content": """SOURCE TYPE: Curated snapshot from the published updates.js operational dataset.

VERIFIED SNAPSHOT
- WK39-26 import timestamp: 2026-09-25T17:12:13.753Z.
- WK39-26: 3,731 effective records from 3,948 source records, 474 parts, 98 lines, 45 customers.
- Date alignment for WK39-26 was OK; weekMismatch=0 and mismatchedDateColumns=0.
- WK39-26 logical volume: 1,250,732.
- 154 consolidated groups and 217 extra duplicate rows were consolidated in WK39-26.
- Publication history includes WK35-26, WK36-26, WK37-26, WK38-26, WK39-26 and WK40-27.
- WK40-27 logical volume in the snapshot: 1,271,030.
- This dataset demonstrates the production-calendar transition from WK39-26 to WK40-27 and the current duplicate-consolidation behavior.

RULE
Treat published operational data as evidence of what was loaded/published, not as proof that every business rule or UI behavior is correct.
""",
            },
        ],
    },
    {
        "project": "excel-qa",
        "notebook_title": "Excel Engineering & QA",
        "sources": [
            {
                "title": "EXCEL_QA_PROJECT_RULES.md — Project Constitution v1",
                "content": """# EXCEL ENGINEERING & QA — PROJECT CONSTITUTION v1

ROLE
This notebook documents deterministic Excel engineering, Power Pivot/Power Query preservation, workbook repair, visual QA and release evidence.

CORE RULES
- Never declare a workbook release-ready only because its ZIP/OOXML package is syntactically valid.
- Separate OPC/package inspection from real Excel Desktop validation.
- Complex workbooks with Power Pivot, PivotTables, slicers, timelines, caches, connections and calcChain require topology-preserving validation.
- Work from a copy for destructive or repair-oriented operations; preserve and verify the original hash/timestamp when the workflow requires read-only validation.
- When Excel reports a recovery log, treat it as primary evidence of a structural incompatibility until the repaired/saved workbook passes inspection and opens cleanly.
- Do not silently delete pivots, slicers, Data Model parts, connections or formulas just to make a workbook open.
- A stale calcChain can be removed/rebuilt by Excel, but the resulting workbook must be reopened and re-inspected.
- Visual/dashboard changes must preserve pivots, slicer connections, model logic and business calculations unless a separately approved functional change is requested.

RELEASE GATE
A strong release gate combines: package inspect -> Excel Desktop open -> refresh where appropriate -> full calculate/rebuild -> save copy -> reopen -> topology comparison -> original integrity check -> user/physical open verification when needed.
""",
            },
            {
                "title": "SETUP.md — Excel Engineering System Runtime Contract",
                "content": """SOURCE TYPE: Curated snapshot from SETUP.md for Excel Engineering System 1.0.0.

VERIFIED CONTENT
- Windows runtime installation creates %USERPROFILE%\\.excel-engineering-runtime and excelqa.cmd.
- Runtime verification uses excelqa.cmd doctor and profile-list.
- The Excel Engineering Orchestrator routes work to specialist skills rather than replacing domain expertise.
- First acceptance test should run against a COPY or safe test workbook.
- inspect performs package-oriented inspection.
- desktop is intended to confirm that a temporary validation copy opens, refreshes, recalculates, saves and reopens while the original remains unchanged.
- Corporate MCP use should restrict allowed roots through EXCELQA_ALLOWED_ROOTS.
- Normal usage should route natural-language Excel requests through the orchestrator and Hilex capacity profile when applicable.
""",
            },
            {
                "title": "ExcelQA_Runtime_Incident_1.1.2_to_1.1.4.md — CalcChain Case",
                "content": """SOURCE TYPE: Curated incident timeline based on saved runtime evidence and user-verified Excel behavior.

TIMELINE
- Runtime 1.1.2: Excel Desktop validation of Capacity_CW38_Alineado_LKG_Clean.xlsx failed because Workbooks.Open could not open the validation copy. The original remained unchanged.
- Runtime 1.1.3: package inspection could pass while Excel Desktop COM open still failed. The validation path included removal of Zone.Identifier only on the temporary copy.
- Runtime 1.1.4: inspection identified an invalid/stale calcChain reference in sheet1 cell BA2 (stale=1, unknown sheet ids=0) on the problematic candidate.
- Excel itself displayed a recovery log removing the formula record from /xl/calcChain.xml.
- After the workbook was opened/repaired/saved by Excel as Capacity_CW38_ExcelRepair_Saved.xlsx, inspection passed with calc_chain_stale_refs=0 and calc_chain_unknown_sheet_ids=0.
- User subsequently reopened the repaired/saved workbook without the previous recovery error.

LESSON
Package PASS and Desktop PASS are distinct evidence. The correct resolution was not merely to suppress the error; it was to let Excel rebuild/save the workbook and then re-inspect the resulting artifact.
""",
            },
            {
                "title": "ExcelQA_Desktop_Failure_Evidence_v1.1.4.md — Negative Test Evidence",
                "content": """SOURCE TYPE: Curated snapshot from excel-engineering-runtime-powershell v1.1.4 desktop evidence.

VERIFIED FAILURE
- Candidate: Capacity_CW38_Alineado_LKG_Clean_CalcChainFixed.xlsx.
- SHA256: cc4a91adaa95047eba9666b8ce26d560720ba8766ce0b5a834b5fb8acc9c4519.
- Desktop validation status: FAIL.
- Checks requested: open_copy, refresh_all, calculate_full_rebuild, save_copy, reopen_copy, topology_compare, original_hash_check.
- Workbooks.Open strategies failed; Protected View edit attempt returned HRESULT 0x800A03EC; repair-open attempt also failed.
- Original remained unchanged.

RULE
Do not interpret a failed Desktop COM automation by itself as proof that Excel is unavailable; isolate whether the failure is environment, trust/MOTW, workbook corruption or application state.
""",
            },
            {
                "title": "Excel_Engineering_Orchestration_and_UI_QA.md — Specialist Routing",
                "content": """SOURCE TYPE: Curated guidance from Excel Engineering setup, UI/UX skill documentation and online capability benchmark.

ESTABLISHED ROUTING
- Excel/Power Pivot discrepancy work routes through GPT reasoning plus Excel Engineering Orchestrator and specialist Power Pivot/manufacturing skills.
- calcChain stale/workbook repair belongs to deterministic Excel-specialist validation; optional external AI models cannot grant release authority.
- Dashboard polish without touching pivots/slicers routes to Excel Dashboard UI/UX Architect.
- A dashboard redesign should produce a visual contract first, then implementation, then visual QA.
- External/optional models may review or generate synthetic evaluation cases but cannot approve PASS_FOR_RELEASE, security containment or irreversible production-data changes.
- Fail-open behavior is required: if an optional provider is missing, out of quota or times out, the Excel specialist workflow continues rather than being blocked.
""",
            },
        ],
    },
]


async def main() -> None:
    results = await asyncio.gather(*(bootstrap_one(p) for p in PROJECTS), return_exceptions=True)
    rendered = []
    failed = False
    for spec, result in zip(PROJECTS, results):
        if isinstance(result, Exception):
            failed = True
            rendered.append({"status": "error", "project": spec["project"], "error": str(result)})
        else:
            rendered.append(result)
    print(json.dumps({"kind": "project_pair_bootstrap", "results": rendered}, ensure_ascii=False))
    if failed:
        raise SystemExit(1)


if __name__ == "__main__":
    asyncio.run(main())
