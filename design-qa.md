# Cassette console refinement QA

final result: passed

## Request and source

Remove every arrow design and refine the existing remote InvoiceCraft console toward the user-selected Cassette Futurism reference. Existing invoicing behavior, stored data and the independent preview services stay intact. The reference supplies materials and proportions; its arrows and illustrative system telemetry are intentionally omitted.

User attachment: `codex-clipboard-8a28c46a-1862-47f6-b5fd-72bfe8702ec2.png`. Its remote review copy is `/Users/yangshuyun/workspace/dev/kimi-s-app-dev-test/tmp/20261028-console-polish/reference.png`, 1487×1058 pixels.

## Visual evidence and normalization

Remote Chromium captures use a 1× device pixel ratio. The source is proportionally fitted and padded to 1440×1024 beside a real 1440×1024 dashboard capture in the same comparison image. Source and implementation were also inspected together in focused hardware and typography crops.

Review artifacts retained in `/Users/yangshuyun/workspace/dev/kimi-s-app-dev-test/tmp/20261028-console-polish`:

- `comparison-full.png`, `comparison-controls.png`, `comparison-typography.png`, `comparison-controls-and-proof.png`
- `browser-qa/01-dashboard-desktop.png`, `04-editor.png`, `06-editor-compact.png`, `07-editor-narrow.png`
- `browser-qa/08-dashboard-narrow.png`, `09-dashboard-1440x900.png`, `10-dashboard-compact.png`, `11-dashboard-320.png`

The task directory also retains before captures, generated asset sources/prompts, isolated test data and browser verification scripts/reports so the comparison and fixes can be reproduced. These artifacts are excluded from the commit.

## Five fidelity surfaces

- Typography: self-hosted IBM Plex Mono supports the UI; VT323 gives financial readouts, local time and brightness a pixel display character. Chinese uses the existing readable fallback. Arrow-only row actions become compact translated text keys.
- Layout: date, time and language share the beige equipment nameplate. NAV, the deep CRT bezel and PWR align below it; the breadcrumb moves inside the screen. Three recent invoices and the primary creation action fit 1440×900. All records remain accessible from the complete list. Compact windows retain editor/preview tabs and a collapsible equipment rack.
- Colors: charcoal/olive hardware, warm ABS casing, green `#74FF9A`, amber `#FFB23E` and restrained orange/rust stripes follow the selected direction. Red stays on warning indicators.
- Assets: isolated transparent ImageGen metal fasteners and a dark rotary dial replace schematic details; the dial texture stays stationary while the separate rectangular live index rotates. Existing ABS texture remains. Both generated components have documented prompts; VT323 ships with its complete OFL license and official source record.
- Copy: real application labels, translated actions and saved financial data remain. No invented online/sync telemetry is copied. Manual invoice state tracking remains explicit.

## Fixes made during review

- Removed directional glyphs from invoice/client actions, return links, sharing and landing CTA. Removed native select chevrons, details markers and number spinners; replaced the old directional favicon.
- Replaced a separate outer toolbar with the top nameplate and an inner CRT breadcrumb; strengthened NAV keycaps, luminous phosphor keys, dial material, bezel and corner fixtures.
- Reduced excess vertical spacing so the primary creation action, account area and three recent rows fit the desktop viewport.
- Stacked narrow-screen amount readings so complete values remain visible. Adapted local time display at 320px.
- Placed the static CRT texture behind content and removed text glow from the paper proof. Corrected the details heading stacking order so its More menu is unobstructed.

## Validation

- All 40 existing pytest tests passed using the existing remote environment and task-isolated temporary databases; two existing dependency deprecation warnings remain.
- Ruff, all 25 Jinja template parses and path-scoped diff checks passed. A source scan found no arrow glyphs in the 30 application UI source files.
- Remote Chromium passed eight interaction groups: arrow-free surfaces, labeled client navigation, persistent display controls, live preview and language changes without input loss, compact editor/mobile keyboard navigation, More menu/public document/PDF access, anonymous surfaces, reduced motion and absence of JavaScript errors.
- Four additional layout/asset checks passed: embedded fonts and hardware assets, full desktop primary action/recent rows/account area, keyboard brightness adjustment, and complete amount/time readings at 1024, 390 and 320 widths.
- Viewports checked: 1440×1024, 1440×900, 1024×768, 390×844 and 320×740.

No unresolved P0/P1/P2 design issues remain. Browser automation used the existing remote Chromium because the in-app automation interface was unavailable. The running preview remains at `http://10.10.10.1:8002/`; native application packaging remains outside this refinement task.
