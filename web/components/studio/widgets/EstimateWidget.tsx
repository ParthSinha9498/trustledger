'use client';
// "Estimate": a custom AG Studio widget that never shows a noisy number without its 95% interval.
// Each row is value ± interval with an error bar; a group the privacy guard hid reads
// "hidden: small group" instead of a number. Registered with a formatShape and AI metadata so Studio's
// widget agent can place and configure it.

import { useEffect, useState } from 'react';
import type { AgAiParamsBuilder, AgAiToolContext, AgWidgetField, AgWidgetParams } from 'ag-studio';
import type { AgWidgetDefinition } from 'ag-studio-react';

type Mapping = { category?: unknown; value: unknown; interval: unknown; hidden?: unknown };
type EstimateFormat = {
  title?: { enabled?: boolean; text?: string };
  subtitle?: { enabled?: boolean; text?: string };
  caption?: { enabled?: boolean; text?: string };
  style?: { unit?: string; sortByValue?: boolean };
};
type EstimateState = { dataMapping: Mapping; format?: EstimateFormat };

type Row = { label: string; value: number | null; interval: number | null; hidden: number };

const fmt = (v: number) => v.toLocaleString(undefined, { maximumFractionDigits: 0 });
const keyOf = (f: AgWidgetField) => (f as unknown as { key?: string }).key ?? f.fieldId;

function EstimateWidget(params: AgWidgetParams<EstimateState & { format: EstimateFormat }>) {
  const { dataMapping, widgetApi, format } = params;
  const [rows, setRows] = useState<Row[] | null>(null);
  const [error, setError] = useState<string | null>(null);

  const cats = (dataMapping.category ?? []) as AgWidgetField[];
  const value = (dataMapping.value ?? [])[0] as AgWidgetField | undefined;
  const interval = (dataMapping.interval ?? [])[0] as AgWidgetField | undefined;
  const hidden = (dataMapping.hidden ?? [])[0] as AgWidgetField | undefined;
  const sortByValue = format?.style?.sortByValue ?? false;

  useEffect(() => {
    if (!value || !interval) {
      widgetApi.setDisplayState('incompleteDataMapping');
      return;
    }
    let live = true;
    widgetApi.setDisplayState('loading');
    const fields = [...cats, value, interval, ...(hidden ? [hidden] : [])];
    widgetApi
      .getData({ fields, sort: cats.length ? cats.map((c) => ({ field: c, direction: 'asc' as const })) as never : undefined })
      .then((res) => {
        if (!live) return;
        const out: Row[] = res.results.rows.map((r) => {
          const label = cats.map((c) => String(r[keyOf(c)] ?? '')).join(' · ') || 'Total';
          const n = (f?: AgWidgetField) => (f && r[keyOf(f)] != null && Number.isFinite(Number(r[keyOf(f)])) ? Number(r[keyOf(f)]) : null);
          const h = n(hidden) ?? 0;
          const v = n(value);
          // A sum over only hidden cells comes back as 0 or blank: that group is hidden, not zero.
          const allHidden = v == null || (v === 0 && h > 0);
          return { label, value: allHidden ? null : v, interval: allHidden ? null : n(interval), hidden: h };
        });
        if (sortByValue) out.sort((a, b) => (b.value ?? -1) - (a.value ?? -1));
        setRows(out);
        setError(null);
        widgetApi.setDisplayState(out.length ? 'displayed' : 'noData');
      })
      .catch((e: unknown) => {
        if (!live) return;
        setError(e instanceof Error ? e.message : String(e));
        widgetApi.setDisplayState('displayed');
      });
    return () => {
      live = false;
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [dataMapping, sortByValue, widgetApi]);

  if (error) return <div className="tl-est tl-est-error">Couldn&apos;t load this estimate: {error}</div>;
  if (!rows) return null;
  const unit = format?.style?.unit ? ` ${format.style.unit}` : '';
  const max = Math.max(1, ...rows.map((r) => (r.value ?? 0) + (r.interval ?? 0)));
  const pct = (x: number) => `${Math.max(0, Math.min(100, (x / max) * 100))}%`;

  if (!cats.length && rows.length === 1) {
    const r = rows[0];
    return (
      <div className="tl-est tl-est-single">
        {r.value == null ? (
          <div className="tl-est-hidden">hidden: small group</div>
        ) : (
          <>
            <div className="tl-est-big">
              {fmt(r.value)}
              {unit}
            </div>
            <div className="tl-est-ci">95% interval (±) {fmt(r.interval ?? 0)}</div>
          </>
        )}
        {r.hidden > 0 && r.value != null && <div className="tl-est-note">Leaves out {r.hidden} hidden small group{r.hidden === 1 ? '' : 's'}</div>}
      </div>
    );
  }

  return (
    <div className="tl-est" role="list">
      {rows.map((r) => (
        <div className="tl-est-row" role="listitem" key={r.label}>
          <div className="tl-est-label" title={r.label}>
            {r.label}
          </div>
          <div className="tl-est-track" aria-hidden>
            {r.value != null && (
              <>
                <div className="tl-est-bar" style={{ width: pct(r.value) }} />
                <div
                  className="tl-est-whisker"
                  style={{ left: pct(r.value - (r.interval ?? 0)), width: `calc(${pct(r.value + (r.interval ?? 0))} - ${pct(r.value - (r.interval ?? 0))})` }}
                />
              </>
            )}
          </div>
          <div className="tl-est-num">
            {r.value == null ? (
              <span className="tl-est-hidden">hidden: small group</span>
            ) : (
              <>
                <b>{fmt(r.value)}</b>
                <span className="tl-est-pm">± {fmt(r.interval ?? 0)}</span>
                {r.hidden > 0 && (
                  <span className="tl-est-flag" title={`${r.hidden} hidden small group${r.hidden === 1 ? '' : 's'} left out of this total`}>
                    +{r.hidden} hidden
                  </span>
                )}
              </>
            )}
          </div>
        </div>
      ))}
      <div className="tl-est-legend">
        Bar = estimate · line = 95% interval (±){rows.some((r) => r.hidden > 0) ? ' · +N hidden = small groups left out of that total' : ''}
        {unit ? ` · ${unit.trim()}` : ''}
      </div>
    </div>
  );
}

const ICON =
  '<svg xmlns="http://www.w3.org/2000/svg" width="32" height="32" viewBox="0 0 32 32" fill="none"><rect x="3" y="7" width="16" height="5" rx="1" fill="var(--ag-chart-palette-fills-1-color, #2563eb)"/><rect x="3" y="19" width="22" height="5" rx="1" fill="var(--ag-chart-palette-fills-1-color, #2563eb)"/><path d="M15 9.5h8M15 7.5v4M23 7.5v4M21 21.5h8M21 19.5v4M29 19.5v4" stroke="currentColor" stroke-width="1.5"/></svg>';

/** The `estimate` widget type: category (optional) + value (sum) + interval measure (+ hidden count). */
export const estimateWidget: AgWidgetDefinition = {
  id: 'estimate',
  label: 'Estimate (± 95% interval)',
  icon: ICON,
  comp: EstimateWidget as never,
  dataMapping: {
    category: {
      type: 'fieldset',
      supportedRoles: ['category', 'temporal', 'numeric'],
      requires: { cardinality: 'many' },
      required: false,
      intent: 'category',
      aiDescription: 'Optional dimension(s) to split the estimate by, e.g. M2.ageBand. Leave empty for one total.',
    },
    value: {
      type: 'field',
      supportedRoles: ['numeric'],
      requires: { cardinality: 'one' },
      required: true,
      intent: 'value',
      aiDescription: 'The noisy estimate, summed: e.g. { id: "M2.value", aggregation: "sum" } (or M4.spend / M6.spend).',
    },
    interval: {
      type: 'field',
      supportedRoles: ['numeric'],
      requires: { cardinality: 'one' },
      required: true,
      intent: 'value',
      aiDescription:
        'The matching 95% interval measure from the SAME table, e.g. { id: "M2_interval" } for M2.value or { id: "M4_spend_interval" } for M4.spend. Never a summed per-cell ci95.',
    },
    hidden: {
      type: 'field',
      supportedRoles: ['numeric'],
      requires: { cardinality: 'one' },
      required: false,
      intent: 'value',
      aiDescription: 'Optional: { id: "<table>.hiddenGroups", aggregation: "sum" } from the same table, to flag totals that leave out hidden small groups.',
    },
  },
  // Studio exports no shape builder for widget formats; defineAiTool hands its params callback the
  // same builder synchronously, so we borrow it there (the tool itself is never registered with an agent).
  formatShape: ({ api }) => {
    let built: unknown;
    api.defineAiTool({
      name: 'estimate_format_shape',
      description: 'internal',
      params: (s: AgAiParamsBuilder) => {
        const title = s
          .object({ enabled: s.boolean().optional(), text: s.string().optional() })
          .optional();
        built = s
          .object({
            title,
            subtitle: title,
            caption: title,
            style: s
              .object({
                unit: s.string({ description: 'Optional unit after the number, e.g. "buyers" or "USD".' }).optional(),
                sortByValue: s.boolean({ description: 'Sort rows by estimate, largest first.' }).optional(),
              })
              .optional(),
          })
          .optional();
        return built as never;
      },
      execute: (_args: unknown, ctx: AgAiToolContext) => ctx.error('not callable'),
    } as never);
    return built as never;
  },
  form: (p) =>
    p.createDefaults({
      dataMappingItems: [
        { key: 'category', label: 'Split by' },
        { key: 'value', label: 'Estimate (sum)' },
        { key: 'interval', label: '95% interval measure' },
        { key: 'hidden', label: 'Hidden small groups (sum)' },
      ],
    }) as never,
  defaultSize: { width: 420, height: 260 },
  minSize: { width: 200, height: 100 },
  ai: {
    label: 'Estimate',
    description:
      'Shows differentially private estimates as value ± 95% interval with an error bar, one row per category; hidden small groups read "hidden: small group".',
    usage:
      'Use for ANY noisy buyer or spend number from tables M1-M6 (prefer it over plain charts for those). Not for exact brand counts (B1-B5); use a grid or chart there.',
    configuration:
      'Map value to sum(<table>.value) (or sum(<table>.spend)), interval to that table\'s "<table>_interval" (or "<table>_spend_interval") measure, hidden to sum(<table>.hiddenGroups), and category to one or two dimensions of the SAME table. Never mix tables in one widget. Set a title saying what is counted.',
  },
};
