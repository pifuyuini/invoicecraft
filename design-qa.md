# Cassette console design QA

final result: passed

## Target and evidence

The user selected Cassette Futurism: a heavy 1970s/1980s console with olive/charcoal hardware, beige plastic housing, embossed labels, a black phosphor CRT, amber/orange/rust stripes, and functioning physical display controls. The generated reference provides art direction; this is a real invoicing application rather than a raster recreation.

Reference and implemented dashboard were inspected together at 1440×1024. The comparison, green/amber captures, editor at desktop/compact/narrow sizes, public document, and settings screenshots are retained in the remote task's `browser-qa/` directory beside the checkout. `report.json` records interaction acceptance.

## Accepted

- NAV, CRT and PWR/SYS form separate equipment modules inside a continuous textured beige housing, with corner screws, hard bevels, inset keycaps and black labels.
- IBM Plex Mono is self-hosted; green and amber phosphors are actual display modes. Numeric financial values remain per currency. Counts and segmented meters derive from saved invoices.
- Brightness range and physical effects toggle work and survive reloads. The timecode is local time, not fabricated system telemetry.
- Grain and scanlines are static, faint and pointer-transparent. Channel snow is finite and stepped; boot text appears one character per 12 Hz tick. Reduced-motion and the effects switch disable the effects. No continuous flashing or smooth easing.
- Red is restricted to small warning lamps. Alerts and overdue amounts use amber. Main amounts and row text were enlarged after visual review.
- Existing live preview, bilingual editing without input loss, keyboard navigation and public/PDF documents remain usable. Paper documents retain a readable cream surface.
- 1024×768 uses editor/preview tabs; 390×844 has no document-level horizontal overflow. The equipment rack is collapsible on smaller windows.

## Validation

All 40 existing pytest cases passed. Ruff, Jinja parsing, translation coverage and diff checks passed. Remote Chromium acceptance verifies display preferences, live preview, language persistence, navigation focus, public/PDF output, reduced motion and absence of page errors.

No unresolved P0/P1/P2 issues remain. Browser testing used the remote existing Chromium because the in-app automation interface was unavailable in this session. Native macOS packaging remains a later task.
