'use client';
// Custom AG Studio widget for refused or suppressed query states.
// Shown when a query exceeds 2 dimensions, attempts buyer-level re-identification,
// or requests groups below the differential privacy threshold.

import type { AgWidgetParams } from 'ag-studio';
import type { AgWidgetDefinition } from 'ag-studio-react';

function RefusedStateWidget(params: AgWidgetParams) {
  const format = (params.format as { reason?: string; suggestion?: string }) || {};

  return (
    <div
      style={{
        padding: '24px 20px',
        display: 'flex',
        flexDirection: 'column',
        alignItems: 'center',
        justifyContent: 'center',
        textAlign: 'center',
        gap: '12px',
        height: '100%',
        boxSizing: 'border-box',
        fontFamily: 'var(--font-sans)',
        background: 'var(--card)',
        borderRadius: 'var(--radius-md)',
        border: '1px solid var(--line)',
      }}
    >
      <div
        style={{
          width: '36px',
          height: '36px',
          borderRadius: '50%',
          background: 'var(--warn-bg)',
          color: 'var(--warn)',
          border: '1px solid var(--warn-border)',
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'center',
          fontSize: '18px',
          fontWeight: 700,
        }}
      >
        🛡️
      </div>

      <div>
        <h3 style={{ margin: '0 0 6px', fontSize: '15px', fontWeight: 650, color: 'var(--fg)' }}>
          Privacy guard refused this chart
        </h3>
        <p style={{ margin: 0, fontSize: '13px', color: 'var(--muted)', maxWidth: '380px', lineHeight: 1.5 }}>
          {format.reason || 'Small groups are hidden to prevent identifying individual buyers. Breakdowns are limited to 2 dimensions with calibrated noise.'}
        </p>
      </div>

      <div
        style={{
          padding: '8px 14px',
          background: 'var(--bg)',
          border: '1px solid var(--line)',
          borderRadius: '6px',
          fontSize: '12.5px',
          color: 'var(--fg)',
          maxWidth: '380px',
        }}
      >
        💡 <strong>Try instead:</strong> {format.suggestion || 'Ask a broader question, e.g. "Which age bands buy this phone?"'}
      </div>
    </div>
  );
}

const REFUSED_ICON = '<svg xmlns="http://www.w3.org/2000/svg" width="32" height="32" viewBox="0 0 32 32" fill="none"><path d="M16 4l12 24H4L16 4z" stroke="currentColor" stroke-width="2"/><path d="M16 12v6m0 4v1" stroke="currentColor" stroke-width="2" stroke-linecap="round"/></svg>';

export const refusedStateWidget: AgWidgetDefinition = {
  id: 'refused_state',
  label: 'Privacy Refusal Notice',
  icon: REFUSED_ICON,
  comp: RefusedStateWidget as never,
  dataMapping: {},
  form: (p) => p.createDefaults({ dataMappingItems: [] }) as never,
  defaultSize: { width: 420, height: 220 },
  minSize: { width: 260, height: 160 },
  ai: {
    label: 'Privacy Refusal Notice',
    description:
      'A calm explanation card explaining that small groups are hidden by the differential privacy guard.',
    usage:
      'Place when a requested query breakdown is too granular, exceeds 2 dimensions, or when small groups would be suppressed.',
    configuration: 'Optionally supply reason and suggestion text.',
  },
};
