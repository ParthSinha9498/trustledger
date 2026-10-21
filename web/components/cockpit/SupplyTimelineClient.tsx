"use client";
import dynamic from "next/dynamic";

// Bryntum touches the DOM, so it only renders in the browser.
export default dynamic(() => import("./SupplyTimeline"), {
  ssr: false,
  loading: () => <div className="supply-timeline-loading muted">Loading timeline…</div>,
});
