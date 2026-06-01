/**
 * Calendar heatmap of daily close moves (ECharts calendar-simple, dark theme).
 * @see https://echarts.apache.org/examples/en/editor.html?c=calendar-simple
 */

import * as echarts from 'echarts/core';
import { HeatmapChart } from 'echarts/charts';
import { CalendarComponent, TooltipComponent, VisualMapComponent } from 'echarts/components';
import { CanvasRenderer } from 'echarts/renderers';
import type { HistorySeriesV1 } from './history-types';
import { dayKeyToISO } from './history-shard-loader';

echarts.use([HeatmapChart, CalendarComponent, TooltipComponent, VisualMapComponent, CanvasRenderer]);

const muted = 'rgba(255, 255, 255, 0.55)';
const border = 'rgba(255, 255, 255, 0.1)';
const tipBg = 'rgba(12, 14, 24, 0.94)';

export type CalendarChartHandle = { dispose: () => void };

function dayKeyToDate(dayKey: number): string {
	return dayKeyToISO(dayKey);
}

/** Daily log-return in percent for calendar cell intensity. */
function buildCalendarData(series: HistorySeriesV1): [string, number][] {
	const out: [string, number][] = [];
	for (let i = 1; i < series.rows; i++) {
		const prev = series.c[i - 1];
		const curr = series.c[i];
		if (!prev || prev <= 0 || !curr) continue;
		const pct = (Math.log(curr / prev) * 100);
		out.push([dayKeyToDate(series.d[i]), Math.round(pct * 100) / 100]);
	}
	return out;
}

export function mountHistoryCalendar(host: HTMLElement, series: HistorySeriesV1): CalendarChartHandle {
	const chart = echarts.init(host);
	const data = buildCalendarData(series);
	if (data.length === 0) {
		chart.setOption({
			title: {
				text: 'Not enough bars for calendar view',
				left: 'center',
				top: 'middle',
				textStyle: { color: muted, fontSize: 12 },
			},
		});
		return { dispose: () => chart.dispose() };
	}

	const years = [...new Set(data.map(([d]) => d.slice(0, 4)))].sort();
	const allYears = years.length ? years : [dayKeyToDate(series.rangeStart).slice(0, 4)];
	const range = allYears.slice(-5);

	let vmin = 0;
	let vmax = 0;
	for (const [, v] of data) {
		if (v < vmin) vmin = v;
		if (v > vmax) vmax = v;
	}
	const cap = Math.max(Math.abs(vmin), Math.abs(vmax), 0.5);

	chart.setOption({
		animation: !window.matchMedia('(prefers-reduced-motion: reduce)').matches,
		tooltip: {
			position: 'top',
			backgroundColor: tipBg,
			borderColor: border,
			textStyle: { color: '#fff', fontSize: 11 },
			formatter: (p: { value?: [string, number] }) => {
				const v = p.value;
				if (!v) return '';
				const sign = v[1] >= 0 ? '+' : '';
				return `<strong>${v[0]}</strong><br/>Daily move: ${sign}${v[1].toFixed(2)}%`;
			},
		},
		visualMap: {
			min: -cap,
			max: cap,
			calculable: true,
			orient: 'horizontal',
			left: 'center',
			bottom: 0,
			textStyle: { color: muted, fontSize: 10 },
			inRange: { color: ['#3d1a4a', '#1a2a38', '#48e0bc'] },
		},
		calendar: range.map((year) => ({
			top: range.length > 1 ? 40 + range.indexOf(year) * 160 : 40,
			range: year,
			cellSize: ['auto', 14],
			splitLine: { lineStyle: { color: 'rgba(255,255,255,0.06)' } },
			itemStyle: { borderWidth: 0.5, borderColor: 'rgba(0,0,0,0.4)' },
			dayLabel: { color: muted, fontSize: 9, firstDay: 1 },
			monthLabel: { color: muted, fontSize: 10, nameMap: 'en' },
			yearLabel: { color: muted, fontSize: 11, margin: 8 },
		})),
		series: range.map((year, idx) => ({
			type: 'heatmap',
			coordinateSystem: 'calendar',
			calendarIndex: idx,
			data: data.filter(([d]) => d.startsWith(year)),
		})),
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
