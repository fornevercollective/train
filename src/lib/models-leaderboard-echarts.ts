/**
 * ECharts mounts for /models — scatter + bars (inspired by leaderboard UIs such as
 * https://artificialanalysis.ai and https://onyx.app/llm-leaderboard). Static illustrative data only.
 */
import * as echarts from 'echarts/core';
import { BarChart, HeatmapChart, RadarChart, ScatterChart } from 'echarts/charts';
import { GridComponent, LegendComponent, RadarComponent, TooltipComponent, TitleComponent, VisualMapComponent } from 'echarts/components';
import { CanvasRenderer } from 'echarts/renderers';
import type { LlmDeskRow, BenchmarkMini } from './models-leaderboard-data';

echarts.use([
	ScatterChart,
	BarChart,
	RadarChart,
	HeatmapChart,
	GridComponent,
	LegendComponent,
	TooltipComponent,
	TitleComponent,
	RadarComponent,
	VisualMapComponent,
	CanvasRenderer,
]);

const tipBg = 'rgba(12, 14, 24, 0.94)';
const border = 'rgba(255, 255, 255, 0.12)';
const muted = 'rgba(255, 255, 255, 0.55)';

function reducedMotion(): boolean {
	return typeof window !== 'undefined' && window.matchMedia('(prefers-reduced-motion: reduce)').matches;
}

function bindResize(chart: echarts.ECharts, el: HTMLElement): () => void {
	const ro = new ResizeObserver(() => chart.resize());
	ro.observe(el);
	const onWin = () => chart.resize();
	window.addEventListener('resize', onWin);
	return () => {
		ro.disconnect();
		window.removeEventListener('resize', onWin);
	};
}

function mountScatterIntelPrice(el: HTMLElement, rows: LlmDeskRow[]): (() => void) | undefined {
	const chart = echarts.init(el, undefined, { renderer: 'canvas' });
	const data = rows.map((r) => ({
		name: r.model,
		value: [r.inputPerM * 0.35 + r.outputPerM * 0.65, r.intelligenceIdx, r.speedTps],
		provider: r.provider,
	}));
	chart.setOption({
		textStyle: { fontFamily: 'Inter, system-ui, sans-serif' },
		grid: { left: 12, right: 18, top: 36, bottom: 44, containLabel: true },
		tooltip: {
			trigger: 'item',
			backgroundColor: tipBg,
			borderColor: border,
			textStyle: { color: 'rgba(255,255,255,0.92)', fontSize: 11 },
			formatter: (p: { data?: { name?: string; value?: number[]; provider?: string } }) => {
				const d = p.data;
				if (!d?.value) return '';
				return `<strong>${d.name}</strong> (${d.provider})<br/>Blend $/1M tok: ${d.value[0].toFixed(2)}<br/>Desk index: ${d.value[1]} · tok/s: ${d.value[2]}`;
			},
		},
		xAxis: {
			name: 'Illustrative $/1M (blend)',
			nameLocation: 'middle',
			nameGap: 28,
			nameTextStyle: { color: muted, fontSize: 10 },
			axisLabel: { color: muted, fontSize: 10 },
			splitLine: { lineStyle: { color: 'rgba(255,255,255,0.06)' } },
		},
		yAxis: {
			name: 'Desk intelligence index',
			nameTextStyle: { color: muted, fontSize: 10 },
			axisLabel: { color: muted, fontSize: 10 },
			splitLine: { lineStyle: { color: 'rgba(255,255,255,0.06)' } },
		},
		series: [
			{
				type: 'scatter',
				symbolSize: (val: number[]) => 14 + (val[2] ?? 50) / 25,
				label: { show: true, position: 'top', color: muted, fontSize: 9, formatter: (p: { name?: string }) => p.name ?? '' },
				data: data.map((d, i) => ({
					...d,
					itemStyle: {
						color: `hsla(${200 + (i * 37) % 120}, 70%, 58%, 0.85)`,
						borderColor: 'rgba(0,0,0,0.35)',
						borderWidth: 1,
					},
				})),
				animationDuration: reducedMotion() ? 0 : 700,
			},
		],
	});
	const off = bindResize(chart, el);
	return () => {
		off();
		chart.dispose();
	};
}

function mountSpeedBar(el: HTMLElement, rows: LlmDeskRow[]): (() => void) | undefined {
	const chart = echarts.init(el, undefined, { renderer: 'canvas' });
	const sorted = [...rows].sort((a, b) => b.speedTps - a.speedTps);
	chart.setOption({
		textStyle: { fontFamily: 'Inter, system-ui, sans-serif' },
		title: {
			text: 'Output tok/s (illustrative)',
			left: 0,
			top: 0,
			textStyle: { color: muted, fontSize: 11, fontWeight: 600, fontFamily: 'IBM Plex Mono, monospace' },
		},
		grid: { left: 4, right: 28, top: 32, bottom: 4, containLabel: true },
		tooltip: {
			trigger: 'axis',
			axisPointer: { type: 'shadow' },
			backgroundColor: tipBg,
			borderColor: border,
			textStyle: { color: 'rgba(255,255,255,0.92)', fontSize: 11 },
		},
		xAxis: {
			type: 'value',
			axisLabel: { color: muted, fontSize: 10 },
			splitLine: { lineStyle: { color: 'rgba(255,255,255,0.06)' } },
		},
		yAxis: {
			type: 'category',
			data: sorted.map((r) => r.model.replace(/\s*\([^)]+\)\s*$/, '')),
			inverse: true,
			axisLabel: { color: muted, fontSize: 10, width: 120, overflow: 'truncate' },
			axisLine: { show: false },
			axisTick: { show: false },
		},
		series: [
			{
				type: 'bar',
				data: sorted.map((r, i) => ({
					value: r.speedTps,
					itemStyle: {
						color: ['#48e0bc', '#78b4ff', '#aa5aff', '#ffd278'][i % 4],
						borderRadius: [0, 8, 8, 0],
					},
				})),
				barMaxWidth: 18,
				animationDuration: reducedMotion() ? 0 : 650,
			},
		],
	});
	const off = bindResize(chart, el);
	return () => {
		off();
		chart.dispose();
	};
}

function mountAgentRadar(el: HTMLElement, rows: LlmDeskRow[]): (() => void) | undefined {
	const chart = echarts.init(el, undefined, { renderer: 'canvas' });
	const top = [...rows].sort((a, b) => b.agentFit - a.agentFit);
	chart.setOption({
		textStyle: { fontFamily: 'Inter, system-ui, sans-serif' },
		tooltip: { backgroundColor: tipBg, borderColor: border, textStyle: { color: 'rgba(255,255,255,0.92)', fontSize: 11 } },
		legend: { bottom: 0, textStyle: { color: muted, fontSize: 10 }, type: 'scroll' },
		radar: {
			center: ['50%', '47%'],
			radius: '66%',
			indicator: [
				{ name: 'Agent', max: 100 },
				{ name: 'Routing', max: 100 },
				{ name: 'Intel', max: 60 },
				{ name: 'Speed', max: 250 },
				{ name: 'Cost-', max: 100 },
			],
			axisName: { color: muted, fontSize: 10 },
			splitLine: { lineStyle: { color: 'rgba(255,255,255,0.08)' } },
			splitArea: { areaStyle: { color: ['rgba(255,255,255,0.02)', 'rgba(255,255,255,0.05)'] } },
			axisLine: { lineStyle: { color: 'rgba(255,255,255,0.08)' } },
		},
		series: [
			{
				type: 'radar',
				data: top.map((r, i) => ({
					name: r.model.replace(/\s*\([^)]+\)\s*$/, ''),
					value: [r.agentFit, r.routingFit, r.intelligenceIdx, Math.min(r.speedTps, 250), Math.max(0, 100 - (r.inputPerM + r.outputPerM) * 4)],
					areaStyle: { opacity: 0.08 },
					lineStyle: { width: 2 },
					itemStyle: { color: ['#48e0bc', '#78b4ff', '#aa5aff', '#ffd278', '#ff7aa2'][i % 5] },
				})),
				animationDuration: reducedMotion() ? 0 : 650,
			},
		],
	});
	const off = bindResize(chart, el);
	return () => {
		off();
		chart.dispose();
	};
}

function mountRoutingMatrix(el: HTMLElement, rows: LlmDeskRow[]): (() => void) | undefined {
	const chart = echarts.init(el, undefined, { renderer: 'canvas' });
	const providers = [...new Set(rows.map((r) => r.provider.split('/')[0].trim()))];
	const categories = [...new Set(rows.map((r) => r.category))];
	const data: [number, number, number][] = [];
	for (let x = 0; x < providers.length; x++) {
		for (let y = 0; y < categories.length; y++) {
			const matches = rows.filter((r) => r.provider.split('/')[0].trim() === providers[x] && r.category === categories[y]);
			data.push([x, y, matches.length ? Math.round(matches.reduce((sum, r) => sum + r.routingFit, 0) / matches.length) : 0]);
		}
	}
	chart.setOption({
		grid: { left: 78, right: 20, top: 18, bottom: 52 },
		tooltip: {
			position: 'top',
			backgroundColor: tipBg,
			borderColor: border,
			textStyle: { color: 'rgba(255,255,255,0.92)', fontSize: 11 },
			formatter: (p: { value?: [number, number, number] }) => {
				const v = p.value;
				if (!v) return '';
				return `${providers[v[0]]} / ${categories[v[1]]}<br/>Routing fit: ${v[2] || 'n/a'}`;
			},
		},
		xAxis: {
			type: 'category',
			data: providers,
			axisLabel: { color: muted, fontSize: 9, rotate: 35, width: 72, overflow: 'truncate' },
			axisTick: { show: false },
		},
		yAxis: {
			type: 'category',
			data: categories,
			axisLabel: { color: muted, fontSize: 10 },
			axisTick: { show: false },
		},
		visualMap: {
			min: 0,
			max: 100,
			show: false,
			inRange: { color: ['rgba(20,25,38,0.8)', '#274b7a', '#48e0bc'] },
		},
		series: [
			{
				type: 'heatmap',
				data,
				label: { show: true, color: 'rgba(255,255,255,0.86)', fontSize: 9 },
				itemStyle: { borderColor: 'rgba(255,255,255,0.06)', borderWidth: 1 },
				animationDuration: reducedMotion() ? 0 : 650,
			},
		],
	});
	const off = bindResize(chart, el);
	return () => {
		off();
		chart.dispose();
	};
}

function mountMiniBar(el: HTMLElement, minis: BenchmarkMini[]): (() => void) | undefined {
	const chart = echarts.init(el, undefined, { renderer: 'canvas' });
	chart.setOption({
		grid: { left: 4, right: 8, top: 4, bottom: 4, containLabel: true },
		xAxis: {
			type: 'value',
			max: 100,
			show: false,
			splitLine: { show: false },
		},
		yAxis: {
			type: 'category',
			data: minis.map((m) => m.label),
			axisLabel: { color: muted, fontSize: 10 },
			axisLine: { show: false },
			axisTick: { show: false },
		},
		series: [
			{
				type: 'bar',
				data: minis.map((m) => ({
					value: m.value,
					itemStyle: { color: 'rgba(120, 200, 255, 0.55)', borderRadius: [0, 6, 6, 0] },
				})),
				barMaxWidth: 14,
				label: {
					show: true,
					position: 'right',
					color: 'rgba(255,255,255,0.88)',
					fontSize: 10,
					formatter: (p: { value?: number }) => `${p.value ?? 0}%`,
				},
				animationDuration: reducedMotion() ? 0 : 500,
			},
		],
	});
	const off = bindResize(chart, el);
	return () => {
		off();
		chart.dispose();
	};
}

export function mountModelsLeaderboard(root: HTMLElement): () => void {
	const disposers: (() => void)[] = [];
	const enc = root.dataset.payload;
	if (!enc) return () => {};
	let payload: { rows: LlmDeskRow[] } | null = null;
	try {
		payload = JSON.parse(decodeURIComponent(enc));
	} catch {
		return () => {};
	}
	if (!payload?.rows?.length) return () => {};

	const sc = root.querySelector<HTMLElement>('[data-models-chart="intel-blend"]');
	if (sc) {
		const d = mountScatterIntelPrice(sc, payload.rows);
		if (d) disposers.push(d);
	}
	const sp = root.querySelector<HTMLElement>('[data-models-chart="speed"]');
	if (sp) {
		const d = mountSpeedBar(sp, payload.rows);
		if (d) disposers.push(d);
	}
	const radar = root.querySelector<HTMLElement>('[data-models-chart="radar"]');
	if (radar) {
		const d = mountAgentRadar(radar, payload.rows);
		if (d) disposers.push(d);
	}
	const matrix = root.querySelector<HTMLElement>('[data-models-chart="matrix"]');
	if (matrix) {
		const d = mountRoutingMatrix(matrix, payload.rows);
		if (d) disposers.push(d);
	}

	for (const el of root.querySelectorAll<HTMLElement>('[data-models-mini]')) {
		const m = el.dataset.modelsMini;
		if (!m) continue;
		try {
			const minis = JSON.parse(decodeURIComponent(m)) as BenchmarkMini[];
			const d = mountMiniBar(el, minis);
			if (d) disposers.push(d);
		} catch {
			/* skip */
		}
	}

	return () => {
		for (const d of disposers) d();
	};
}
