// AG Studio theme bound to TrustLedger's design tokens (web/app/globals.css). Every colour is a CSS
// variable, and globals.css swaps those variables under prefers-color-scheme: dark, so Studio, its
// grids and its charts follow the app's light/dark mode with no second theme.

import { studioTheme } from 'ag-studio';

const v = (name: string) => `var(--${name})`;
const line = (color: string) => ({ width: 1, color: v(color) });

// Categorical chart colours from the app's semantic tokens (accent first, like the cockpit charts).
const PALETTE = ['accent', 'ok', 'warn', 'bad', 'muted', 'accent-hover', 'ok-hover', 'bad-hover'];
const palette = Object.fromEntries(
  PALETTE.flatMap((t, i) => [
    [`chartPaletteFills${i + 1}Color`, v(t)],
    [`chartPaletteStrokes${i + 1}Color`, v(t)],
  ]),
);

export const trustLedgerStudioTheme = studioTheme.withParams({
  fontFamily: v('font-sans'),
  fontSize: 14,
  textColor: v('fg'),
  foregroundColor: v('fg'),
  subtleTextColor: v('muted'),
  backgroundColor: v('card'),
  borderColor: v('line'),
  accentColor: v('accent'),
  iconColor: v('muted'),
  rowHoverColor: v('chip'),

  studioWrapperBorder: false,
  studioWrapperBorderRadius: 0,
  studioWrapperSpacing: 0,
  studioWrapperBackgroundColor: v('bg'),
  studioCanvasBorder: false,
  studioCanvasBorderRadius: 0,
  studioCanvasShadow: false,
  studioCanvasBackgroundColor: v('bg'),
  studioCanvasPadding: 12,
  studioCanvasRowHeight: 18,
  studioCanvasFontFamily: v('font-sans'),

  studioWidgetBackgroundColor: v('card'),
  studioWidgetBorder: line('line'),
  studioWidgetBorderRadius: 14,
  studioWidgetPadding: 12,
  studioWidgetTitleFontFamily: v('font-sans'),
  studioWidgetTitleFontSize: 15,
  studioWidgetTitleFontWeight: 600,
  studioWidgetTitleTextColor: v('fg'),
  studioWidgetSubtitleFontFamily: v('font-sans'),
  studioWidgetSubtitleFontSize: 13,
  studioWidgetSubtitleTextColor: v('muted'),
  studioWidgetCaptionFontFamily: v('font-sans'),
  studioWidgetCaptionFontSize: 12,
  studioWidgetCaptionTextColor: v('muted'),
  studioWidgetResizeBorderColor: v('accent'),

  studioPanelContainerBackgroundColor: v('card'),
  studioPanelContainerBorder: line('line'),
  studioPanelContainerBorderRadius: 0,
  studioPanelDividerColor: v('line'),
  studioPanelDividerActiveColor: v('accent'),
  studioPanelSectionBorderColor: v('line'),
  studioPanelHeaderFontFamily: v('font-sans'),
  studioPanelHeaderFontWeight: 600,
  studioPanelChevronButtonHoverBackgroundColor: v('chip'),
  studioPanelChevronButtonHoverColor: v('accent'),
  studioToggleButtonActiveBackgroundColor: v('accent-bg'),
  studioToggleButtonActiveBorderColor: v('accent'),
  studioToggleButtonActiveColor: v('accent'),

  gridFontFamily: v('font-sans'),
  gridFontSize: 14,
  gridCellTextColor: v('fg'),
  gridHeaderBackgroundColor: v('card'),
  gridHeaderTextColor: v('muted'),
  gridHeaderFontWeight: 600,
  gridHeaderFontSize: 13,
  gridRowHeight: 36,
  gridRowBorder: line('line-subtle'),
  gridHeaderRowBorder: line('line'),
  gridPinnedRowBorder: line('line'),
  gridRowHoverColor: v('chip'),
  gridWrapperBorder: false,

  chartFontFamily: v('font-sans'),
  chartTextColor: v('fg'),
  chartSubtleTextColor: v('muted'),
  chartAxisLineColor: v('line'),
  chartGridLineColor: v('line-subtle'),
  ...palette,
} as never);
