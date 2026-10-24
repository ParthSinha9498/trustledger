"use client";
import { AllCommunityModule, ModuleRegistry, themeQuartz, type ColDef } from "ag-grid-community";
import { AgGridReact } from "ag-grid-react";

ModuleRegistry.registerModules([AllCommunityModule]);

// Follows the app's CSS variables, so light and dark mode match the rest of the page.
const theme = themeQuartz.withParams({
  backgroundColor: "var(--card)",
  foregroundColor: "var(--fg)",
  borderColor: "var(--line)",
  chromeBackgroundColor: "var(--bg)",
  headerBackgroundColor: "var(--bg)",
  accentColor: "var(--accent)",
  browserColorScheme: "inherit",
  fontFamily: "var(--font-sans)",
  fontSize: 13,
  headerFontWeight: 600,
  wrapperBorderRadius: 10,
  spacing: 6,
  rowHoverColor: "var(--chip)",
});
// Auto-height grids that always have rows: no empty band under a 3-row result.
const tightTheme = theme.withParams({ autoHeightMinBodyHeight: 0 });
// Narrow cards: less padding inside each cell, so a value and its ± range fit a phone without sideways scrolling.
const DENSE = { cellHorizontalPadding: 10 };
const denseTheme = theme.withParams(DENSE);
const denseTightTheme = tightTheme.withParams(DENSE);

export default function Grid<T>({ rows, columns, height = 360, onRowClick, autoHeight = false, dense = false }: {
  rows: T[];
  columns: ColDef<T>[];
  height?: number;
  onRowClick?: (row: T) => void;
  /** Grow with the rows instead of a fixed height (use for small result sets). */
  autoHeight?: boolean;
  /** Tighter cell padding (phone-width cards). */
  dense?: boolean;
}) {
  const tight = autoHeight && rows.length > 0;
  return (
    <div style={autoHeight ? { width: "100%", minWidth: 0 } : { height, width: "100%", minWidth: 0 }} className={onRowClick ? "grid-clickable" : undefined}>
      <AgGridReact<T>
        theme={dense ? (tight ? denseTightTheme : denseTheme) : tight ? tightTheme : theme}
        rowData={rows}
        columnDefs={columns}
        domLayout={autoHeight ? "autoHeight" : "normal"}
        defaultColDef={{ flex: 1, minWidth: 90, sortable: true, filter: true, resizable: true }}
        onRowClicked={(e) => e.data && onRowClick?.(e.data)}
      />
    </div>
  );
}
