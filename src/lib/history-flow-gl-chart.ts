/**
 * WebGL flow field from real daily log-returns and volume bands (ECharts flowGL).
 * X-axis = trading days (oldest→newest); vector direction/magnitude = that day's return.
 */

import * as echarts from 'echarts/core';
import { GridComponent, TooltipComponent } from 'echarts/components';
import { CanvasRenderer } from 'echarts/renderers';
import type { HistorySeriesV1 } from './history-types';
import { dayKeyToISO } from './history-shard-loader';

let flowGlReady: Promise<void> | null = null;
let flowGlRegistered = false;

async function ensureFlowGl(): Promise<void> {
	if (flowGlRegistered) return;
	if (!flowGlReady) {
		flowGlReady = (async () => {
			await import('echarts-gl');
			const { FlowGLChart } = await import('echarts-gl/charts');
			echarts.use([FlowGLChart, GridComponent, TooltipComponent, CanvasRenderer]);
			flowGlRegistered = true;
		})();
	}
	await flowGlReady;
}

const muted = 'rgba(255, 255, 255, 0.55)';

export type FlowGlChartHandle = { dispose: () => void };

export type FlowGlMeta = {
	gridW: number;
	gridH: number;
	startDate: string;
	endDate: string;
	returns: number[];
	volumes: number[];
};

const MAX_DAYS = 96;
const VOL_BANDS = 12;

function dailyLogReturns(series: HistorySeriesV1): { returns: number[]; volumes: number[]; dates: number[] } {
	const returns: number[] = [];
	const volumes: number[] = [];
	const dates: number[] = [];
	for (let i = 1; i < series.c.length; i++) {
		const a = series.c[i - 1];
		const b = series.c[i];
		if (!a || a <= 0 || !b) continue;
		returns.push(Math.log(b / a));
		volumes.push(series.v[i] ?? 0);
		dates.push(series.d[i]);
	}
	return { returns, volumes, dates };
}

function rollingVol(returns: number[], index: number, window = 20): number {
	const start = Math.max(0, index - window + 1);
	let sum = 0;
	let n = 0;
	for (let i = start; i <= index; i++) {
		sum += returns[i] * returns[i];
		n++;
	}
	return n ? Math.sqrt(sum / n) : 0;
}

/** Velocity grid tied to actual OHLCV: each column is one trading day. */
export function buildFlowVectorData(series: HistorySeriesV1): {
	data: number[][];
	gridW: number;
	gridH: number;
	meta: FlowGlMeta;
} {
	const { returns, volumes, dates } = dailyLogReturns(series);
	if (!returns.length) {
		return {
			data: [[0, 0, 0, 0]],
			gridW: 1,
			gridH: 1,
			meta: { gridW: 1, gridH: 1, startDate: '', endDate: '', returns: [], volumes: [] },
		};
	}

	const tail = Math.min(returns.length, MAX_DAYS);
	const r = returns.slice(-tail);
	const v = volumes.slice(-tail);
	const d = dates.slice(-tail);
	const gridW = r.length;
	const gridH = VOL_BANDS;

	const vols = r.map((_, i) => rollingVol(r, i));
	const maxVol = Math.max(...vols, 1e-8);
	const maxAbsRet = Math.max(...r.map(Math.abs), 1e-6);

	const data: number[][] = [];
	for (let x = 0; x < gridW; x++) {
		const ret = r[x];
		const volBucket = Math.min(gridH - 1, Math.floor((vols[x] / maxVol) * (gridH - 1)));
		const scale = 1.2 / maxAbsRet;
		const vx = ret * scale;
		const vy = 0.05 * (v[x] / Math.max(...v, 1));
		for (let y = 0; y < gridH; y++) {
			if (y === volBucket) {
				data.push([x, y, vx, vy]);
			} else {
				data.push([x, y, 0, 0]);
			}
		}
	}

	return {
		data,
		gridW,
		gridH,
		meta: {
			gridW,
			gridH,
			startDate: dayKeyToISO(d[0]),
			endDate: dayKeyToISO(d[d.length - 1]),
			returns: r,
			volumes: v,
		},
	};
}

export async function mountHistoryFlowGL(
	host: HTMLElement,
	series: HistorySeriesV1,
): Promise<FlowGlChartHandle> {
	await ensureFlowGl();
	const chart = echarts.init(host, undefined, { renderer: 'canvas' });
	const { data, gridW, gridH, meta } = buildFlowVectorData(series);
	const reduced = window.matchMedia('(prefers-reduced-motion: reduce)').matches;

	const tickStep = Math.max(1, Math.floor(gridW / 6));
	const xLabels: Record<number, string> = {};
	for (let x = 0; x < gridW; x += tickStep) {
		const dayKey = series.d[series.d.length - gridW + x];
		if (dayKey) xLabels[x] = dayKeyToISO(dayKey).slice(0, 7);
	}

	chart.setOption({
		backgroundColor: 'transparent',
		grid: { left: 36, right: 8, top: 32, bottom: 22 },
		tooltip: {
			trigger: 'item',
			backgroundColor: 'rgba(12,14,24,0.94)',
			borderColor: 'rgba(255,255,255,0.12)',
			textStyle: { color: '#fff', fontSize: 11 },
			formatter: (p: { value?: number[] }) => {
				const v = p.value;
				if (!v || v.length < 2) return '';
				const x = Math.round(v[0]);
				const idx = Math.min(Math.max(x, 0), meta.returns.length - 1);
				const ret = meta.returns[idx];
				const pct = (ret * 100).toFixed(2);
				return `<strong>${meta.startDate}</strong> → <strong>${meta.endDate}</strong><br/>Day ${x + 1}/${gridW}: ${pct}% log-return<br/>Vol band: ${Math.round(v[1])}`;
			},
		},
		xAxis: {
			type: 'value',
			min: 0,
			max: gridW - 1,
			axisLabel: { color: muted, fontSize: 9, formatter: (val: number) => xLabels[val] ?? '' },
			splitLine: { show: false },
		},
		yAxis: {
			type: 'value',
			min: 0,
			max: gridH - 1,
			axisLabel: {
				color: muted,
				fontSize: 9,
				formatter: (val: number) => (val === 0 ? 'low vol' : val === gridH - 1 ? 'high vol' : ''),
			},
			splitLine: { lineStyle: { color: 'rgba(255,255,255,0.06)' } },
		},
		series: [
			{
				type: 'flowGL',
				coordinateSystem: 'cartesian2d',
				data,
				dimensions: ['x', 'y', 'vx', 'vy'],
				gridWidth: gridW,
				gridHeight: gridH,
				particleType: 'line',
				particleDensity: reduced ? 40 : 64,
				particleSpeed: reduced ? 0.6 : 1.2,
				particleSize: 2,
				particleTrail: 1.5,
				itemStyle: {
					color: 'rgba(120, 200, 255, 0.95)',
					opacity: 0.85,
				},
			},
		],
		graphic: [
			{
				type: 'text',
				left: 8,
				top: 6,
				style: {
					text: `${series.ticker} · flow = daily log-return (→ time), row = vol band`,
					fill: muted,
					fontSize: 10,
				},
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
