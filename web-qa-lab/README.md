# Web QA Lab v1

Reusable pre-delivery QA harness for HLMQ web/HTML applications.

## Goal

The user should not be the first tester. A release candidate must pass deterministic browser QA and visual review before physical validation.

## Workflow

1. Build / serve the candidate.
2. Set `QA_BASE_URL`.
3. Run Playwright on desktop, tablet and mobile.
4. Generate `artifacts/results.json`, HTML report, screenshots/traces/videos on failures.
5. Run the release gate.
6. Review the candidate visually in a real browser session (TinyFish/Cloud Browser when accessible).
7. Compare critical behavior against the Last Known Good release.
8. Only then mark **READY FOR PHYSICAL TEST**.

## Install

```bash
cd web-qa-lab
npm install
npm run install:browsers
```

## Run

```bash
QA_BASE_URL=http://127.0.0.1:8080 npm run qa
npm run report
```

For a deployed candidate:

```bash
QA_BASE_URL=https://candidate.example.com npm run qa
npm run report
```

## Current automatic gates

- Entry page HTTP status < 400.
- Visible, non-empty body.
- No uncaught JavaScript errors.
- No `console.error` output.
- Visible interactive controls remain inside the viewport.
- Focusable controls expose perceivable focus feedback.
- No horizontal page overflow.
- Critical headings are not clipped.
- Full-page release-candidate screenshots on desktop/tablet/mobile.

## Project-specific layer

Each application should add tests under `tests/projects/<project>/` for business-critical flows. Example for Programa de Producción:

- Dashboard opens.
- Sidebar/navigation works.
- FY selector preserves historical context.
- Multi-select filters work.
- Charts render with expected bands/labels.
- Tables retain fixed headers and usable scrolling.
- Admin/Data Center opens.
- Import/export does not corrupt state.
- No regression in LKG flows.

## Release policy

- **READY FOR PHYSICAL TEST**: deterministic checks pass and agent visual review has no critical findings.
- **PASS WITH OBSERVATIONS**: functionality passes, only non-blocking visual issues remain.
- **FAIL — FIX BEFORE DELIVERY**: any critical functional, console, navigation, data-state, overflow or regression failure.

Physical validation remains the final authority for environments that cannot be fully reproduced in cloud/browser automation.
