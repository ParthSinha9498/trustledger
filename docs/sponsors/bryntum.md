# How we used Bryntum Scheduler

> Note: a "What you're looking at" strip and extra timeline markers are being added in a parallel PR (`ag/bryntum`).
> This page describes what is on `main` today and will be updated after that PR merges.

## What it does in TrustLedger
When a checkout fails with "not in this store's supply chain", the brand wants to know where the unit left its
planned route. The Bryntum Scheduler on `/cockpit/supply-chain` draws the brand's own shipping records week by week:
one row per brand, distributor and store; a bar per batch at each stop; dependency lines from the brand to the
distributor to the stores the batch was shipped to. Units that sold at a store the batch was never shipped to get a
red bar and a red line from the distributor, and that store's row is tinted red ("Store, not on the route").
The same view, filtered to the case's product and store, is embedded on each investigation page.

All of it is exact business data (batches, shipments, unit counts per store), shown only to that brand. No serial
numbers and no buyer data are sent to the browser.

## Where
- Scheduler component: [`web/components/cockpit/supply-chain/Timeline.tsx:140-192`](../../web/components/cockpit/supply-chain/Timeline.tsx)
  (`BryntumScheduler`, read-only, `dependenciesFeature`, `timeRangesFeature` for the "This week" line, custom `eventTooltipFeature`).
- Package: [`web/package.json:10-11`](../../web/package.json) (`@bryntum/scheduler` aliased to `@bryntum/scheduler-trial`, plus `@bryntum/scheduler-react`).
- Page: [`web/app/cockpit/supply-chain/page.tsx`](../../web/app/cockpit/supply-chain/page.tsx) (product and store filters, kept in the URL so a filtered view can be shared, lines 66-73).
- Case page embed: [`web/app/cockpit/cases/[id]/page.tsx:287`](../../web/app/cockpit/cases/%5Bid%5D/page.tsx) via
  [`SupplyChainPanel.tsx`](../../web/components/cockpit/supply-chain/SupplyChainPanel.tsx) (falls back to the whole product when no batch ever reached the case's store, lines 30-33).
- Client-only load: `next/dynamic` with `ssr: false`, [`SupplyChainView.tsx:9-12`](../../web/components/cockpit/supply-chain/SupplyChainView.tsx).

## Data flow
1. The browser calls `GET /supply-chain?sku=&store_id=` on the public API:
   [`backend/api/supply_chain.py:12-30`](../../backend/api/supply_chain.py). The API holds no brand data; it proxies.
2. The API calls the brand node's `GET /v1/supply-chain` (node token required):
   [`backend/brand_node/supply_chain.py:52-53`](../../backend/brand_node/supply_chain.py). The response is already shaped for a
   scheduler (`resources`, `events`, `dependencies`, `off_channel`, `totals`; docstring lines 4-13). Everything is aggregated
   per batch; off-channel events and their dependency lines carry `highlight: true` (lines 124-130).
3. `Timeline.tsx` maps that onto Bryntum stores: rows sorted brand, distributors, then off-route stores first
   (lines 85-102); events coloured by kind (lines 18-20, 104-112); dependency types start-to-start / end-to-start (lines 25-26, 114-119).
4. Tests: [`tests/test_supply_chain.py`](../../tests/test_supply_chain.py) (node token required, wrong brand refused,
   no serials in the response, the planted diversion is highlighted).

## What we built on top
- Week axis: a custom `weekAndMonth` preset whose month header shortens or hides a label for a month cut short at either
  end, instead of clipping it (`Timeline.tsx:32-48`), and range padding so the edge months have room (lines 50-60).
- Fit or scroll: every week fits on screen when columns stay readable; otherwise the scheduler scrolls to the latest weeks
  (lines 124-135). "Only those batches" / "All batches" toggle narrows the timeline to the off-channel batches
  (`SupplyChainView.tsx:63-70`).
- Plain-language tooltips: what the bar is, batch and product, where, which weeks, units (`Timeline.tsx:176-191`), HTML-encoded.
- An AG Grid table of the off-channel rows and a one-line summary built only from those rows sit above the timeline
  ([`OffChannelTable.tsx`](../../web/components/cockpit/supply-chain/OffChannelTable.tsx)).

## Theming and dark mode
- Light: Bryntum's `svalbard-light` theme (`Timeline.tsx:6`). Dark: `svalbard-dark` loaded only under
  `prefers-color-scheme: dark` ([`timeline.css:2`](../../web/components/cockpit/supply-chain/timeline.css)), plus overrides that map
  headers, rows and grid lines onto the app's CSS variables (lines 24-47). The app follows the OS setting.
- Red leak styling for highlighted events, dependency lines and off-route rows: `timeline.css:13-17`.

## Phone fallback
Below 700 px wide (`page.tsx:8`) the scheduler is not rendered. The page shows the off-channel table with fewer columns
(`OffChannelTable.tsx:17-46`) and a note that the week-by-week timeline needs a wider screen (`SupplyChainView.tsx:72-76`);
the case page shows a link to the full supply chain page instead.

## Screenshots
- [`docs/media/06_supply_chain.png`](../media/06_supply_chain.png): supply chain page, stats and off-channel table above the timeline.
