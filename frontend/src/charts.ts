import * as echarts from "echarts/core";
import { HeatmapChart, LineChart, PieChart } from "echarts/charts";
import {
  AriaComponent,
  CalendarComponent,
  GridComponent,
  LegendComponent,
  TitleComponent,
  TooltipComponent,
  VisualMapComponent,
} from "echarts/components";
import { CanvasRenderer } from "echarts/renderers";
import ReactEChartsCoreModule from "echarts-for-react/lib/core";

echarts.use([
  LineChart,
  PieChart,
  HeatmapChart,
  AriaComponent,
  CalendarComponent,
  GridComponent,
  LegendComponent,
  TitleComponent,
  TooltipComponent,
  VisualMapComponent,
  CanvasRenderer,
]);

// echarts-for-react publishes this CommonJS entry with a nested default when
// consumed through native ESM. Normalize it once so React receives a component.
const ReactEChartsCore = (
  ReactEChartsCoreModule as unknown as { default: typeof ReactEChartsCoreModule }
).default;

export { echarts, ReactEChartsCore };
