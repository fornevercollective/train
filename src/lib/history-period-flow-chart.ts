/**
 * Three OHLCV-linked return flow panels (month / week / day) with flowGL + candle bars.
 */

import * as echarts from 'echarts/core';
import { BarChart } from 'echarts/charts';
import { GridComponent, TooltipComponent } from 'echarts/components';
import { CanvasRenderer } from 'echarts/renderers';
import type { HistorySeriesV1 } from './history-types';
import {
	buildDayBuckets,
	buildMonthBuckets,
	buildWeekBuckets,
	type PeriodBucket,
} from './history-return-aggregates';

let flowGlReady: Promise<void> | null = null;
let flowGlRegistered = false;

async function ensureFlowGl(): Promise<void> {
	if (flowGlRegistered) return;
	if (!flowGlReady) {
		flowGlReady = (async () => {
			await import('echarts-gl');
			const { FlowGLChart } = await import('echarts-gl/charts');
			echarts.use([FlowGLChart, BarChart, GridComponent, TooltipComponent, CanvasRenderer]);
			flowGlRegistered = true;
		})();
	}
	await flowGlReady;
}

const muted = 'rgba(255, 255, 255, 0.55)';
const upColor = '#48e0bc';
const downColor = '#ff7890';
const tipBg = 'rgba(12, 14, 24, 0.94)';

export type PeriodFlowHandle = { dispose: () => void };

export type PeriodFlowMode = 'month' | 'week' | 'day';

function scaleMag(pct: number, cap: number): number {
	return Math.min(Math.abs(pct) / Math.max(cap, 0.01), 1.4) * Math.sign(pct || 0);
}

/** flowGL grid: vx = time (→), vy = return sign (up pos / down neg). */
function buildFlowGrid(
	buckets: PeriodBucket[],
	mode: PeriodFlowMode,
): { data: number[][]; gridW: number; gridH: number } {
	const gridW = Math.max(buckets.length, 1);
	const gridH = mode === 'week' ? 4 : 3;
	const cap = Math.max(...buckets.map((b) => Math.abs(b.returnPct)), 0.5);
	const data: number[][] = [];

	for (let x = 0; x < gridW; x++) {
		const b = buckets[x];
		const mag = scaleMag(b.returnPct, cap);
		const wMag =
			b.weekendReturnPct !== undefined ? scaleMag(b.weekendReturnPct, cap) : 0;

		for (let y = 0; y < gridH; y++) {
			if (mode === 'month' && y === 1) {
				data.push([x, y, 0.25, mag]);
			} else if (mode === 'week' && y === 1) {
				data.push([x, y, 0.22, mag]);
			} else if (mode === 'week' && y === 2 && b.weekendReturnPct !== undefined) {
				data.push([x, y, 0.08, wMag]);
			} else if (mode === 'day' && y === 1) {
				data.push([x, y, 0.2, mag]);
			} else {
				data.push([x, y, 0, 0]);
			}
		}
	}
	return { data, gridW, gridH };
}

function panelTitle(mode: PeriodFlowMode): string {
	if (mode === 'month') return 'Month flow · close→close per calendar month (↑ pos / ↓ neg)';
	if (mode === 'week') return 'Week flow · ISO week trend; lower band = Fri→Mon weekend gap';
	return 'Day flow · daily log-return (→ time), ↑ up day / ↓ down day';
}

function formatDataStrip(buckets: PeriodBucket[], mode: PeriodFlowMode): string {
	const tail = buckets.slice(-6);
	return tail
		.map((b) => {
			const sign = b.returnPct >= 0 ? '+' : '';
			let s = `${b.label} ${sign}${b.returnPct.toFixed(2)}%`;
			if (mode === 'week' && b.weekendReturnPct !== undefined) {
				const ws = b.weekendReturnPct >= 0 ? '+' : '';
				s += ` · wknd ${ws}${b.weekendReturnPct.toFixed(2)}%`;
			}
			return s;
		})
		.join(' · ');
}

export async function mountPeriodReturnFlow(
	host: HTMLElement,
	series: HistorySeriesV1,
	mode: PeriodFlowMode,
	dataStripEl?: HTMLElement | null,
): Promise<PeriodFlowHandle> {
	await ensureFlowGl();
	const buckets =
		mode === 'month'
			? buildMonthBuckets(series)
			: mode === 'week'
				? buildWeekBuckets(series)
				: buildDayBuckets(series);

	if (!buckets.length) {
		host.innerHTML = '<p class="muted" style="padding:8px;font-size:11px;">Not enough bars.</p>';
		if (dataStripEl) dataStripEl.textContent = '';
		return { dispose: () => {} };
	}

	if (dataStripEl) {
		dataStripEl.textContent = formatDataStrip(buckets, mode);
		dataStripEl.title = buckets.map((b) => b.reason).join('\n');
	}

	const chart = echarts.init(host, undefined, { renderer: 'canvas' });
	const { data, gridW, gridH } = buildFlowGrid(buckets, mode);
	const labels = buckets.map((b) => b.label);
	const barData = buckets.map((b) => b.returnPct);
	const weekendBar =
		mode === 'week' ? buckets.map((b) => b.weekendReturnPct ?? null) : null;
	const reduced = window.matchMedia('(prefers-reduced-motion: reduce)').matches;
	const cap = Math.max(...barData.map(Math.abs), 0.5);

	chart.setOption({
		backgroundColor: 'transparent',
		grid: { left: 40, right: 8, top: 36, bottom: mode === 'day' ? 28 : 22 },
		tooltip: {
			trigger: 'axis',
			axisPointer: { type: 'shadow' },
			backgroundColor: tipBg,
			borderColor: 'rgba(255,255,255,0.12)',
			textStyle: { color: '#fff', fontSize: 11 },
			formatter: (params: { dataIndex?: number }[]) => {
				const idx = params[0]?.dataIndex ?? 0;
				const b = buckets[idx];
				if (!b) return '';
				let html = `<strong>${b.label}</strong><br/>${b.reason}`;
				if (b.weekendReason) html += `<br/><span style="opacity:0.85">${b.weekendReason}</span>`;
				return html;
			},
		},
		xAxis: [
			{
				type: 'category',
				data: labels,
				axisLabel: {
					color: muted,
					fontSize: 8,
					interval: mode === 'day' ? Math.max(0, Math.floor(labels.length / 8) - 1) : 0,
					rotate: mode === 'day' ? 45 : 0,
				},
				axisLine: { lineStyle: { color: 'rgba(255,255,255,0.1)' } },
			},
			{
				type: 'value',
				min: 0,
				max: gridW - 1,
				show: false,
			},
		],
		yAxis: [
			{
				type: 'value',
				min: -cap * 1.15,
				max: cap * 1.15,
				axisLabel: {
					color: muted,
					fontSize: 9,
					formatter: (v: number) => `${v.toFixed(1)}%`,
				},
				splitLine: { lineStyle: { color: 'rgba(255,255,255,0.06)' } },
			},
			{
				type: 'value',
				min: 0,
				max: gridH - 1,
				show: false,
			},
		],
		series: [
			{
				type: 'bar',
				xAxisIndex: 0,
				yAxisIndex: 0,
				data: barData,
				barMaxWidth: mode === 'day' ? 6 : 14,
				itemStyle: {
					color: (p: { value: number }) => (p.value >= 0 ? upColor : downColor),
					borderRadius: [2, 2, 0, 0],
				},
				z: 3,
			},
			...(weekendBar
				? [
						{
							type: 'bar' as const,
							xAxisIndex: 0,
							yAxisIndex: 0,
							data: weekendBar,
							barMaxWidth: 8,
							barGap: '-100%',
							itemStyle: {
								color: (p: { value: number | null }) =>
									p.value === null ? 'transparent' : p.value >= 0 ? 'rgba(72,224,188,0.45)' : 'rgba(255,120,144,0.45)',
							},
							z: 2,
						},
					]
				: []),
			{
				type: 'flowGL',
				xAxisIndex: 1,
				yAxisIndex: 1,
				coordinateSystem: 'cartesian2d',
				data,
				dimensions: ['x', 'y', 'vx', 'vy'],
				gridWidth: gridW,
				gridHeight: gridH,
				particleType: 'line',
				particleDensity: reduced ? 28 : 48,
				particleSpeed: reduced ? 0.5 : 1,
				particleSize: 1.8,
				particleTrail: 1,
				silent: true,
				itemStyle: { color: 'rgba(120, 200, 255, 0.75)', opacity: 0.7 },
				z: 1,
			},
		],
		graphic: [
			{
				type: 'text',
				left: 8,
				top: 4,
				style: { text: panelTitle(mode), fill: muted, fontSize: 9, width: host.clientWidth - 16 },
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

export type ReturnFlowStackHandle = {
	dispose: () => void;
};

export async function mountReturnFlowStack(
	monthHost: HTMLElement,
	weekHost: HTMLElement,
	dayHost: HTMLElement,
	series: HistorySeriesV1,
	strips?: { month?: HTMLElement | null; week?: HTMLElement | null; day?: HTMLElement | null },
): Promise<ReturnFlowStackHandle> {
	const handles = await Promise.all([
		mountPeriodReturnFlow(monthHost, series, 'month', strips?.month),
		mountPeriodReturnFlow(weekHost, series, 'week', strips?.week),
		mountPeriodReturnFlow(dayHost, series, 'day', strips?.day),
	]);
	return {
		dispose() {
			for (const h of handles) h.dispose();
		},
	};
}
