# How we used Bryntum Scheduler

## What it does in TrustLedger
When a checkout fails with "not in this store's supply chain", the brand wants to know where the unit left its
planned route. The Bryntum Scheduler on `/cockpit/supply-chain` draws the brand's own shipping records week by week:
one row per brand, distributor and store; a bar per batch at each stop; dependency lines from the brand to the
distributor to the stores the batch was shipped to. Units that sold at a store the batch was never shipped to get a
red bar and a red line from the distributor, and that store's row is tinted red ("Store, not on the route").
A three-line "What you're looking at" strip above the timeline says what the picture shows, and pointing at a line
highlights its part of the timeline.
The same view, filtered to the case's product and store, is embedded on each investigation page.

All of it is exact business data (batches, shipments, unit counts per store), shown only to that brand. No serial
numbers and no buyer data are sent to the browser.

## Where
- Scheduler component: [`web/components/cockpit/supply-chain/Timeline.tsx:153-214`](../../web/components/cockpit/supply-chain/Timeline.tsx)
  (`BryntumScheduler`, read-only, `dependenciesFeature`, `timeRangesFeature` for the "This week" line, custom `eventRenderer` and `eventTooltipFeature`).
- Package: [`web/package.json:10-11`](../../web/package.json) (`@bryntum/scheduler` aliased to `@bryntum/scheduler-trial`, plus `@bryntum/scheduler-react`).
- Page: [`web/app/cockpit/supply-chain/page.tsx`](../../web/app/cockpit/supply-chain/page.tsx) (product and store filters, kept in the URL so a filtered view can be shared, lines 66-73).
- Case page embed: [`web/app/cockpit/cases/[id]/page.tsx:287`](../../web/app/cockpit/cases/%5Bid%5D/page.tsx) via
  [`SupplyChainPanel.tsx`](../../web/components/cockpit/supply-chain/SupplyChainPanel.tsx) (falls back to the whole product when no batch ever reached the case's store, lines 30-33).
- Client-only load: `next/dynamic` with `ssr: false`, [`SupplyChainView.tsx:10-14`](../../web/components/cockpit/supply-chain/SupplyChainView.tsx).

## Data flow
1. The browser calls `GET /supply-chain?sku=&store_id=` on the public API:
   [`backend/api/supply_chain.py:12-30`](../../backend/api/supply_chain.py). The API holds no brand data; it proxies.
2. The API calls the brand node's `GET /v1/supply-chain` (node token required):
   [`backend/brand_node/supply_chain.py:52-53`](../../backend/brand_node/supply_chain.py). The response is already shaped for a
   scheduler (`resources`, `events`, `dependencies`, `off_channel`, `totals`; docstring lines 4-13). Everything is aggregated
   per batch; off-channel events and their dependency lines carry `highlight: true` (lines 123-131).
3. `Timeline.tsx` maps that onto Bryntum stores: rows sorted brand, distributors, then off-route stores first
   (lines 97-114); events coloured by kind (lines 18-20, 116-124); dependency types start-to-start / end-to-start (lines 28-29, 126-132).
4. Tests: [`tests/test_supply_chain.py`](../../tests/test_supply_chain.py) (node token required, wrong brand refused,
   no serials in the response, the planted diversion is highlighted).

## What we built on top
- "What you're looking at" strip: three numbered lines above the timeline, built only from the API response
  (`leakStory`, [`SupplyChainView.tsx:29-57`](../../web/components/cockpit/supply-chain/SupplyChainView.tsx)):
  1. where the batches were shipped (distributor and stores), 2. how many units sold at which store instead,
  3. "That mismatch is the leak". Line 2 says the distributor "never supplies" that store only when the response
  proves it (lines 42-47); otherwise it says the batches were not shipped there.
- Hover or click to highlight: pointing at a strip line (hover or keyboard focus) highlights it, a click pins it
  (`SupplyChainView.tsx:75-77, 120-137`). The line number is passed to the scheduler (`highlight` prop, line 155), which tags
  rows, bars and dependency lines into three groups: g1 the planned route, g2 the store where the units sold, g3 the red
  leak bars and lines (`Timeline.tsx:90-94, 112, 123, 131`). The highlight is pure CSS on the wrapper class
  (`Timeline.tsx:151`, [`timeline.css:22-34`](../../web/components/cockpit/supply-chain/timeline.css)): the chosen group stays bright, the rest dims.
- On-chart markers: each red bar is labelled "batch · first sold at Store C · wk of …" (the store name comes from the data)
  and starts with a flag drawn by a custom `eventRenderer` (`Timeline.tsx:119, 168-175`); its tooltip adds
  "First sold here in the week of …" (line 209).
- Plain legend: "Sent out by the brand", "At the distributor", "Shipped to this store", "Sold at a store it wasn't shipped to",
  the flag ("First sale at that store") and "This week" (`SupplyChainView.tsx:16-21, 148-154`).
- Default "Only those batches": the timeline opens narrowed to the batches in the off-channel table, with an
  "All batches" toggle (`SupplyChainView.tsx:69, 72, 103-110`).
- Week axis: a custom `weekAndMonth` preset whose month header shortens or hides a label for a month cut short at either
  end, instead of clipping it (`Timeline.tsx:35-51`), and range padding so the edge months have room (lines 53-63).
- Fit or scroll: every week fits on screen when columns stay readable; otherwise the scheduler scrolls to the latest weeks
  (lines 137-148).
- Plain-language tooltips: what the bar is, batch and product, where, which weeks, units (`Timeline.tsx:197-213`), HTML-encoded.
- An AG Grid table of the off-channel rows sits above the timeline
  ([`OffChannelTable.tsx`](../../web/components/cockpit/supply-chain/OffChannelTable.tsx)).

## Theming and dark mode
- Light: Bryntum's `svalbard-light` theme (`Timeline.tsx:6`). Dark: `svalbard-dark` loaded only under
  `prefers-color-scheme: dark` ([`timeline.css:2`](../../web/components/cockpit/supply-chain/timeline.css)), plus overrides that map
  headers, rows and grid lines onto the app's CSS variables (lines 39-62). The app follows the OS setting.
- Red leak styling for highlighted events, dependency lines and off-route rows: `timeline.css:13-17`.

## Phone fallback
Below 700 px wide (`page.tsx:8`) the scheduler is not rendered. The page shows the off-channel table with fewer columns
(`OffChannelTable.tsx:17-46`), the same three strip lines as a plain numbered text summary (`SupplyChainView.tsx:112-118`),
and a note that the week-by-week timeline needs a wider screen (`SupplyChainView.tsx:139-143`);
the case page shows a link to the full supply chain page instead.

## Screenshots
- [`docs/media/06_supply_chain.png`](../media/06_supply_chain.png): supply chain page, stats and off-channel table above the timeline.
