/**
 * Compact 5-year price sparkline driven by ECharts.
 *
 * Used by the listing page once the history loader hands us a HistorySeriesV1.
 * The chart is intentionally minimalist: a single area line, no axis labels, a
 * tooltip that surfaces the exact close on hover. The returned object exposes
 * `dispose` for cleanup if the host element is removed.
 */

import * as echarts from 'echarts/core';
import { LineChart } from 'echarts/charts';
import {
	GridComponent,
	TooltipComponent,
	DataZoomComponent,
	MarkLineComponent,
} from 'echarts/components';
import { CanvasRenderer } from 'echarts/renderers';
import type { HistorySeriesV1 } from './history-types';
import { dayKeyToISO } from './history-shard-loader';

echarts.use([
	LineChart,
	GridComponent,
	TooltipComponent,
	DataZoomComponent,
	MarkLineComponent,
	CanvasRenderer,
]);

const muted = 'rgba(255, 255, 255, 0.55)';
const accent = 'rgba(120, 200, 255, 0.95)';
const accentSoft = 'rgba(120, 200, 255, 0.18)';
const tipBg = 'rgba(12, 14, 24, 0.94)';

export type SparklineHandle = {
	dispose: () => void;
};

export function mountHistorySparkline(
	host: HTMLElement,
	series: HistorySeriesV1,
): SparklineHandle {
	const chart = echarts.init(host);
	const data: [string, number][] = series.d.map((dayKey, index) => [
		dayKeyToISO(dayKey),
		series.c[index],
	]);

	chart.setOption({
		animation: !window.matchMedia('(prefers-reduced-motion: reduce)').matches,
		grid: { left: 8, right: 8, top: 16, bottom: 24 },
		tooltip: {
			trigger: 'axis',
			backgroundColor: tipBg,
			borderColor: 'rgba(255,255,255,0.12)',
			textStyle: { color: '#fff', fontSize: 12 },
			formatter: (params: { name: string; value: [string, number] }[]) => {
				if (!Array.isArray(params) || params.length === 0) return '';
				const [{ value }] = params;
				if (!value) return '';
				const [date, close] = value;
				return `<strong>${date}</strong><br/>Close: $${Number(close).toFixed(2)}`;
			},
		},
		xAxis: {
			type: 'time',
			axisLine: { lineStyle: { color: muted } },
			axisLabel: {
				color: muted,
				fontSize: 10,
				formatter: (value: number) => {
					const date = new Date(value);
					return date.toLocaleString(undefined, { year: 'numeric', month: 'short' });
				},
			},
			splitLine: { show: false },
		},
		yAxis: {
			type: 'value',
			scale: true,
			axisLine: { show: false },
			axisLabel: {
				color: muted,
				fontSize: 10,
				formatter: (value: number) => `$${value.toFixed(value >= 100 ? 0 : 2)}`,
			},
			splitLine: { lineStyle: { color: 'rgba(255,255,255,0.06)' } },
		},
		series: [
			{
				name: series.ticker,
				type: 'line',
				symbol: 'none',
				smooth: false,
				sampling: 'lttb',
				lineStyle: { width: 1.5, color: accent },
				areaStyle: {
					color: new echarts.graphic.LinearGradient(0, 0, 0, 1, [
						{ offset: 0, color: accent },
						{ offset: 1, color: accentSoft },
					]),
					opacity: 0.55,
				},
				data,
			},
		],
	});

	const ro = new ResizeObserver(() => chart.resize());
	ro.observe(host);
	const onWin = () => chart.resize();
	window.addEventListener('resize', onWin);

	return {
		dispose() {
			ro.disconnect();
			window.removeEventListener('resize', onWin);
			chart.dispose();
		},
	};
}
