// Every custom AG Studio widget TrustLedger registers. StudioInsights passes this array to
// createWidgets({ additionalTypes }) and lists the ids first in the widget menu, so a new widget
// only needs to be added here.
import { estimateWidget } from './EstimateWidget';

export const STUDIO_WIDGETS = [estimateWidget];
