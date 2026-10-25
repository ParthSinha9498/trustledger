'use client';
// Custom AG Studio widget showing lifetime privacy budget (rho spent vs 0.25 total limit).
// Reads GET /console/budget and explains the guarantee in plain words.

import { useEffect, useState } from 'react';
import type { AgWidgetParams } from 'ag-studio';
import type { AgWidgetDefinition } from 'ag-studio-react';
import { api, type Budget } from '@/lib/api';

function BudgetMeterWidget({ widgetApi }: AgWidgetParams) {
  const [budget, setBudget] = useState<Budget | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    let live = true;
    widgetApi.setDisplayState('loading');
    api<Budget>('/console/budget')
      .then((b) => {
        if (!live) return;
        setBudget(b);
        widgetApi.setDisplayState('displayed');
      })
      .catch((e: Error) => {
        if (!live) return;
        setError(e.message || 'Failed to load budget');
        widgetApi.setDisplayState('displayed');
      });
    return () => {
      live = false;
    };
  }, [widgetApi]);

  if (error) {
    return <div style={{ padding: '16px', color: 'var(--bad)', fontSize: '13px' }}>{error}</div>;
  }

  if (!budget) return null;

  const spent = Number(budget.spent ?? 0);
  const total = Number(budget.total ?? (budget.remaining != null ? spent + budget.remaining : 0.25));
  const pct = Math.min(100, Math.max(0, total > 0 ? (spent / total) * 100 : 0));

  return (
    <div
      style={{
        padding: '16px 20px',
        display: 'flex',
        flexDirection: 'column',
        justifyContent: 'center',
        gap: '10px',
        height: '100%',
        boxSizing: 'border-box',
        fontFamily: 'var(--font-sans)',
      }}
    >
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'baseline' }}>
        <span style={{ fontWeight: 650, fontSize: '14px', color: 'var(--fg)' }}>Privacy budget used</span>
        <span style={{ fontSize: '13px', color: 'var(--muted)', fontWeight: 600 }}>
          {pct.toFixed(1)}% (ρ {spent.toFixed(2)} / {total.toFixed(2)})
        </span>
      </div>

      <div
        style={{
          width: '100%',
          height: '10px',
          background: 'var(--line)',
          borderRadius: '999px',
          overflow: 'hidden',
        }}
      >
        <div
          style={{
            width: `${pct}%`,
            height: '100%',
            background: pct > 85 ? 'var(--bad)' : pct > 60 ? 'var(--warn)' : 'var(--ok)',
            transition: 'width 0.4s ease',
          }}
        />
      </div>

      <p style={{ margin: 0, fontSize: '12px', color: 'var(--muted)', lineHeight: 1.4 }}>
        Lifetime privacy allowance for this brand. Repeated questions and pre-computed releases cost nothing more.
      </p>
    </div>
  );
}

const BUDGET_ICON = '<svg xmlns="http://www.w3.org/2000/svg" width="32" height="32" viewBox="0 0 32 32" fill="none"><circle cx="16" cy="16" r="12" stroke="currentColor" stroke-width="2"/><path d="M16 8v8l5 5" stroke="currentColor" stroke-width="2" stroke-linecap="round"/></svg>';

export const budgetMeterWidget: AgWidgetDefinition = {
  id: 'budget_meter',
  label: 'Privacy Budget Meter',
  icon: BUDGET_ICON,
  comp: BudgetMeterWidget as never,
  dataMapping: {},
  form: (p) => p.createDefaults({ dataMappingItems: [] }) as never,
  defaultSize: { width: 360, height: 140 },
  minSize: { width: 220, height: 100 },
  ai: {
    label: 'Privacy Budget Meter',
    description:
      'Shows the brand\'s lifetime differential privacy budget spent vs remaining (rho used out of 0.25).',
    usage:
      'Place on the dashboard to visualize how much of the brand\'s privacy guarantee has been consumed.',
    configuration: 'No fields required; reads from the console budget API automatically.',
  },
};
