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
  fontFamily: "inherit",
  fontSize: 13,
  headerFontWeight: 600,
  wrapperBorderRadius: 8,
  spacing: 6,
});

export default function Grid<T>({ rows, columns, height = 360, onRowClick, autoHeight = false }: {
  rows: T[];
  columns: ColDef<T>[];
  height?: number;
  onRowClick?: (row: T) => void;
  /** Grow with the rows instead of a fixed height (use for small result sets). */
  autoHeight?: boolean;
}) {
  return (
    <div style={autoHeight ? { width: "100%" } : { height, width: "100%" }} className={onRowClick ? "grid-clickable" : undefined}>
      <AgGridReact<T>
        theme={theme}
        rowData={rows}
        columnDefs={columns}
        domLayout={autoHeight ? "autoHeight" : "normal"}
        defaultColDef={{ flex: 1, minWidth: 90, sortable: true, filter: true, resizable: true }}
        onRowClicked={(e) => e.data && onRowClick?.(e.data)}
      />
    </div>
  );
}
