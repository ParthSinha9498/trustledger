'use client';
// AG Studio on /cockpit/studio. Client only (loaded with next/dynamic, ssr: false). Data = the private
// release cells + exact brand counts from GET /console/release/cells; nothing else is loaded.

import { useEffect, useMemo, useState } from 'react';
import { AgStudioAiModule, AgStudioLicenseManager, type AgStudioMode } from 'ag-studio';
import { AgStudio, AgStudioProvider, createWidgets } from 'ag-studio-react';
import { API, judgedFetch } from '@/lib/api';
import { buildAi } from './ai';
import { buildStudioData, type Names, type ReleaseCells } from './data';
import { STUDIO_WIDGETS } from './widgets';
import { initialReport, type StudioView } from './initialReport';
import { trustLedgerStudioTheme } from './theme';
import './studio.css';

const licenseKey = process.env.NEXT_PUBLIC_AG_GRID_LICENSE;
if (typeof window !== 'undefined' && licenseKey) {
  try {
    AgStudioLicenseManager.setLicenseKey(licenseKey);
  } catch {
    /* ignore invalid or dry-run keys */
  }
}

type LlmMode = 'unknown' | 'mock' | 'model';

/**
 * fetch for /ai/turn that notices a mock answer. The server marks mock turns with the
 * X-TrustLedger-LLM: mock header; if CORS hides that header, the scripted stream's own
 * `"model": "mock"` chunk is the fallback signal. The body is passed through unchanged.
 */
function mockAwareFetch(onMode: (m: LlmMode) => void): typeof fetch {
  return async (input, init) => {
    const res = await judgedFetch(typeof input === 'string' ? input : input instanceof URL ? input.href : input.url, init);
    const header = res.headers.get('X-TrustLedger-LLM');
    if (header === 'mock') onMode('mock');
    else if (res.headers.get('X-TrustLedger-Model')) onMode('model');
    if (header || !res.ok || !res.body) return res;
    const [a, b] = res.body.tee();
    void (async () => {
      const reader = b.getReader();
      const dec = new TextDecoder();
      let seen = '';
      try {
        while (seen.length < 4000) {
          const { done, value } = await reader.read();
          if (done) break;
          seen += dec.decode(value, { stream: true });
          if (/"model":\s*"mock"/.test(seen)) {
            onMode('mock');
            break;
          }
        }
      } catch {
        /* the reader only watches */
      } finally {
        reader.cancel().catch(() => {});
      }
    })();
    return new Response(a, { status: res.status, statusText: res.statusText, headers: res.headers });
  };
}

export default function StudioInsights() {
  const [cells, setCells] = useState<ReleaseCells | null>(null);
  const [names, setNames] = useState<Names>({});
  const [err, setErr] = useState<string | null>(null);
  const [llm, setLlm] = useState<LlmMode>('unknown');
  // Desktop opens with the analyst panel (edit mode); phones open on the report and can open it.
  const [narrow] = useState(() => window.matchMedia('(max-width: 900px)').matches);
  const [mode, setMode] = useState<AgStudioMode>(narrow ? 'view' : 'edit');
  // ?view=supply opens the supply-chain page; the two tabs in the bar link to each other.
  const [view] = useState<StudioView>(() =>
    typeof window !== 'undefined' && new URLSearchParams(window.location.search).get('view') === 'supply' ? 'supply' : 'insights',
  );

  useEffect(() => {
    let live = true;
    Promise.all([
      judgedFetch(`${API}/console/release/cells`, { cache: 'no-store' }).then(async (r) => {
        if (!r.ok) throw new Error(r.status === 404 ? 'No private release yet for this brand.' : `Release cells: HTTP ${r.status}`);
        return (await r.json()) as ReleaseCells;
      }),
      judgedFetch(`${API}/stores`, { cache: 'no-store' })
        .then((r) => (r.ok ? r.json() : []))
        .then((rows: { store_id: string; name?: string }[]) => Object.fromEntries(rows.filter((s) => s.name).map((s) => [s.store_id, s.name as string])))
        .catch(() => ({})),
    ])
      .then(([c, n]) => {
        if (!live) return;
        setNames(n);
        setCells(c);
      })
      .catch((e: unknown) => live && setErr(e instanceof Error ? (e.message.includes('fetch') ? "Can't reach the TrustLedger API." : e.message) : String(e)));
    return () => {
      live = false;
    };
  }, []);

  const data = useMemo(() => (cells ? buildStudioData(cells, names) : null), [cells, names]);
  // Read once when Studio is created.
  const ai = useMemo(
    () => (cells ? buildAi({ cells, names, apiBase: API, fetch: mockAwareFetch((m) => setLlm(m)) }) : undefined),
    [cells, names],
  );
  // Our widget first in the menu, then Studio's own.
  const widgets = useMemo(
    () => (w: { menu: { label: string; widgetIds: readonly string[] }[] }) =>
      createWidgets({
        additionalTypes: STUDIO_WIDGETS,
        menu: [{ label: 'TrustLedger', widgetIds: STUDIO_WIDGETS.map((d) => d.id) }, ...w.menu],
      } as never),
    [],
  );
  const initialState = useMemo(
    () => ({
      ...initialReport(narrow, view),
      panels: { ai: { collapsed: false, width: 360 }, edit: { collapsed: true }, data: { collapsed: true } },
    }),
    [view],
  );

  return (
    <section className="tl-studio-shell">
      <div className="tl-studio-bar">
        <div className="tl-studio-badges">
          {cells && (
            <span className="badge badge-dp" title="Every buyer number on this page comes from the one-time private release">
              Private release · ε ≈ {cells.epsilon} · no new budget
            </span>
          )}
          {llm === 'mock' && (
            <span className="badge tl-mock" data-testid="mock-ai-badge" title="LLM_MODE=mock: the analyst's answer is a scripted placeholder">
              Mock AI (no model called)
            </span>
          )}
        </div>
        <div className="tl-studio-views" role="tablist" aria-label="Studio pages">
          <a role="tab" aria-selected={view === 'insights'} className="tl-studio-view" href="/cockpit/studio">
            Market insights
          </a>
          <a role="tab" aria-selected={view === 'supply'} className="tl-studio-view" href="/cockpit/studio?view=supply">
            Supply chain
          </a>
        </div>
        {(
          <button
            type="button"
            className="button secondary tl-studio-toggle"
            onClick={() => {
              const next: AgStudioMode = mode === 'edit' ? 'view' : 'edit';
              setMode(next);
            }}
          >
            {mode === 'edit' ? 'Hide analyst' : 'Ask the analyst'}
          </button>
        )}
      </div>
      <div className="tl-studio-frame">
        {err ? (
          <div className="tl-studio-msg">{err}</div>
        ) : !data ? (
          <div className="tl-studio-msg skeletonText">Loading the private release…</div>
        ) : (
          <AgStudioProvider modules={[AgStudioAiModule]}>
            <AgStudio
              style={{ height: '100%', width: '100%' }}
              theme={trustLedgerStudioTheme}
              layout={{ widgetBorderEnabled: true, ...(narrow ? { minWidth: 320 } : {}) } as never}
              data={data}
              ai={ai}
              widgets={widgets as never}
              initialState={initialState}
              mode={mode}
              panels={{ edit: { right: narrow ? ['ai'] : ['ai', 'edit', 'data'] } } as never}
            />
          </AgStudioProvider>
        )}
      </div>
    </section>
  );
}
