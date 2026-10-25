# How we used AG Grid and AG Charts

## What it does in TrustLedger
AG Grid and AG Charts carry every table and chart in the brand's cockpit:
- **Investigations** (`/cockpit`): KPI tiles with small AG Charts (area sparkline or donut), a stacked weekly column chart
  of failed authenticity checks (switchable by reason or by store), and the case list as an AG Grid with custom cell renderers.
- **Insights** (`/cockpit/console`): each answer is shown as an AG Grid table plus an AG Charts bar chart. PayPal-side
  answers are privacy-protected estimates, so every number carries its 95% interval (±).
- **Supply chain** (`/cockpit/supply-chain` and the case page): the "units sold where they weren't shipped" table is an AG Grid.

## Edition
Community only today: [`web/package.json:13-16`](../../web/package.json) (`ag-charts-community`, `ag-charts-react`,
`ag-grid-community`, `ag-grid-react`). Modules registered with `AllCommunityModule` in
[`web/components/Grid.tsx:5`](../../web/components/Grid.tsx) and [`web/components/cockpit/chartTheme.ts:4`](../../web/components/cockpit/chartTheme.ts).

## Where
- Shared grid wrapper: [`web/components/Grid.tsx:30-53`](../../web/components/Grid.tsx) (sortable, filterable, resizable columns;
  optional auto height and a dense mode for phone-width cards; row click handler).
- Case list grid: [`web/app/cockpit/page.tsx:118-135`](../../web/app/cockpit/page.tsx) (columns), rows open the case (lines 290-291).
- Failed-checks chart: [`web/components/cockpit/BlockedChart.tsx:31-76`](../../web/components/cockpit/BlockedChart.tsx) (stacked bar series, reason/store toggle).
- KPI tiles: [`web/components/cockpit/KpiTile.tsx:20-49`](../../web/components/cockpit/KpiTile.tsx), used at `web/app/cockpit/page.tsx:187-203`.
- Insights answers: [`web/components/cockpit/ResultView.tsx:187-192`](../../web/components/cockpit/ResultView.tsx) (Grid + BarChart),
  rendered from `web/app/cockpit/console/page.tsx:172`; bar chart in [`web/components/cockpit/BarChart.tsx`](../../web/components/cockpit/BarChart.tsx).
- Off-channel table: [`web/components/cockpit/supply-chain/OffChannelTable.tsx:17-46`](../../web/components/cockpit/supply-chain/OffChannelTable.tsx).

## What we built on top
- **Custom cell renderers** in the case list (`page.tsx:120, 127, 128, 132-133`): short case reference, status pill,
  confidence dots, and a "Run" pill (Running, Live AI, Offline mock, Replay, ...) computed with a `valueGetter` from `modeOf` (lines 54-70).
- **Value formatters** turn IDs into names (store, product, reason) and dates into short dates (`page.tsx:121-123, 134`).
- **Interval display:** grid cells show `value ± range` with a non-breaking space so a narrow cell wraps before the "±",
  never inside the range (`ResultView.tsx:63-67`, used as `valueFormatter` at lines 95 and 101). Column widths are
  computed from the rendered text so values fit a phone without sideways scrolling (`ResultView.tsx:115-125`).
- **Chart tooltips** carry the same range, because Community has no error bars (`BarChart.tsx:9`, tooltip renderer lines 72-81).
- **Stable colours:** chart series use fixed categorical slots, so a colour always means the same reason or store
  (`chartTheme.ts:6-9`, `BlockedChart.tsx:36-39, 62`).
- **Phone layouts:** the off-channel table drops to four columns and removes filter buttons that would squeeze the headers
  (`OffChannelTable.tsx:37-45`).

## Theming and dark mode
- AG Grid: `themeQuartz.withParams(...)` bound to the app's CSS variables (`--card`, `--fg`, `--line`, `--accent`, ...),
  so one theme follows light and dark mode (`Grid.tsx:7-28`).
- AG Charts: `chartTheme(dark)` picks `ag-default` / `ag-default-dark` and sets fonts and ink to match `globals.css`
  (`chartTheme.ts:11-31`); `useDarkMode` follows the OS setting ([`useDarkMode.ts`](../../web/components/cockpit/useDarkMode.ts)).

## AG Studio (in progress)
Being built in a separate PR; this section will be filled in once it merges.

## Screenshots
- [`docs/media/04_cockpit_case.png`](../media/04_cockpit_case.png): investigation case page.
- [`docs/media/05_console_aggregate.png`](../media/05_console_aggregate.png): an Insights answer, AG Grid with ± ranges next to an AG Charts bar chart.
- [`docs/media/06_supply_chain.png`](../media/06_supply_chain.png): off-channel AG Grid table on the supply chain page.
