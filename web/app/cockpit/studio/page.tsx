"use client";
// AG Studio Insights. Studio is browser-only (and ~1.8 MB), so it loads on this route alone, without SSR.
import dynamic from "next/dynamic";

const StudioInsights = dynamic(() => import("@/components/studio/StudioInsights"), {
  ssr: false,
  loading: () => <div className="card skeleton" style={{ height: 620 }} aria-label="Loading Studio" />,
});

export default function StudioPage() {
  return (
    <main className="wide">
      <div className="page-head">
        <div>
          <h1>Studio</h1>
          <p className="muted">An AI analyst that answers questions about buyers without ever seeing a buyer.</p>
        </div>
      </div>
      <StudioInsights />
    </main>
  );
}
