// The page Studio opens on, so it is useful before anyone types: two Estimate widgets (value ± 95%
// interval) and an AG Grid table of one marginal. Field ids are '<table>.<field>' from ./data.ts.

import type { AgReportState, AgWidgetLayoutState } from 'ag-studio';
import { intervalMeasureId } from './data';

const at = (xTrack: number, yTrack: number, xSpan: number, ySpan: number): AgWidgetLayoutState => ({ xTrack, yTrack, xSpan, ySpan });
const title = (text: string) => ({ enabled: true, text });
const sum = (id: string) => ({ id, aggregation: 'sum' as const });

export const PRODUCT_FOCUS = 'Nimbus P8 128GB';

/** Desktop: two estimates side by side over the grid. Phones: everything stacked full width. */
export const initialReport = (narrow: boolean) => ({
  selectedPageId: 'insights',
  pages: [
    {
      id: 'insights',
      widgets: {
        'p8-age': {
          type: 'estimate',
          dataMapping: {
            category: [{ id: 'M2.ageBand' }],
            value: [sum('M2.value')],
            interval: [{ id: intervalMeasureId('M2') }],
            hidden: [sum('M2.hiddenGroups')],
          },
          format: {
            title: title(`Buyers of the ${PRODUCT_FOCUS} by age band`),
            subtitle: title('All stores · private release M2'),
          },
        },
        'spend-store': {
          type: 'estimate',
          dataMapping: {
            category: [{ id: 'M4.store' }],
            value: [sum('M4.spend')],
            interval: [{ id: intervalMeasureId('M4', true) }],
            hidden: [sum('M4.hiddenGroups')],
          },
          format: {
            title: title('Total spend by store (USD)'),
            subtitle: title('Private release M4'),
            style: { sortByValue: true },
          },
        },
        'm6-grid': {
          type: 'grid',
          dataMapping: {
            cols: [
              { id: 'M6.store' },
              { id: 'M6.product' },
              sum('M6.value'),
              { id: intervalMeasureId('M6') },
              sum('M6.spend'),
              { id: intervalMeasureId('M6', true) },
              sum('M6.hiddenGroups'),
            ],
          },
          format: { title: title('Buyers and spend by store and product (M6)') },
        },
        'budget-meter': {
          type: 'budget_meter',
          format: { title: title('Differential Privacy Budget (zCDP)') },
        },
        'refused-notice': {
          type: 'refused_state',
          format: {
            title: title('Detailed Buyer Cross-Tabulation'),
            reason: 'Small groups are hidden: cells with fewer than 10 buyers are suppressed to prevent re-identification.',
            suggestion: 'View higher-level aggregates in M1 or M2.',
          },
        },
      },
      widgetLayout: {
        'p8-age': narrow ? at(0, 0, 24, 21) : at(0, 0, 12, 16),
        'spend-store': narrow ? at(0, 21, 24, 21) : at(12, 0, 12, 16),
        'budget-meter': narrow ? at(0, 42, 24, 12) : at(0, 16, 12, 14),
        'refused-notice': narrow ? at(0, 54, 24, 12) : at(12, 16, 12, 14),
        'm6-grid': narrow ? at(0, 66, 24, 22) : at(0, 30, 24, 22),
      },
      filter: {
        widget: {
          'p8-age': [{ field: { id: 'M2.product' }, model: { operator: 'equals', value: PRODUCT_FOCUS } }],
        },
      },
    },
  ],
}) as unknown as AgReportState;
